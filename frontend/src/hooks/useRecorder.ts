/**
 * Microphone capture + live transport.
 *
 * Real behaviour, no simulation:
 *  - getUserMedia -> Web Audio -> AudioWorklet (ScriptProcessor fallback)
 *  - Float32 frames -> mono 16-bit PCM -> binary WebSocket frames
 *  - level + waveform come from an AnalyserNode reading the actual microphone
 *  - if the socket is unavailable the same PCM is buffered and uploaded as a
 *    WAV on stop, so dictation still works
 *  - partial transcripts are shown ONLY when the backend forwards real ones
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, liveSocketUrl, tokenStore } from '@/services/api'
import type { OutputMode, SpeechResult } from '@/types'

export type RecorderState =
  | 'idle'
  | 'requesting'
  | 'recording'
  | 'stopping'
  | 'processing'
  | 'done'
  | 'error'

export interface RecorderOptions {
  mode: OutputMode
  context: string
  languageCode: string | null
  includeOutputs: string[]
  noiseReduction: boolean
  retainAudio?: boolean
  maxSeconds?: number
  onFinal?: (result: SpeechResult) => void
  onPartial?: (text: string) => void
  onNotice?: (message: string) => void
  onError?: (message: string) => void
}

const TARGET_RATE = 16000
const WORKLET_SOURCE = `
class PCMCapture extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      this.port.postMessage(input[0].slice(0));
    }
    return true;
  }
}
registerProcessor('pcm-capture', PCMCapture);
`

function downsample(buffer: Float32Array, from: number, to: number): Float32Array {
  if (to >= from) return buffer
  const ratio = from / to
  const length = Math.floor(buffer.length / ratio)
  const out = new Float32Array(length)
  for (let i = 0; i < length; i++) {
    const start = Math.floor(i * ratio)
    const end = Math.min(buffer.length, Math.floor((i + 1) * ratio))
    let sum = 0
    for (let j = start; j < end; j++) sum += buffer[j]
    out[i] = sum / Math.max(1, end - start)
  }
  return out
}

function toInt16(samples: Float32Array): Int16Array {
  const out = new Int16Array(samples.length)
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return out
}

function buildWav(chunks: Int16Array[], sampleRate: number): Blob {
  const total = chunks.reduce((n, c) => n + c.length, 0)
  const buffer = new ArrayBuffer(44 + total * 2)
  const view = new DataView(buffer)
  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + total * 2, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeStr(36, 'data')
  view.setUint32(40, total * 2, true)
  let offset = 44
  for (const chunk of chunks) {
    for (let i = 0; i < chunk.length; i++, offset += 2) view.setInt16(offset, chunk[i], true)
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

export function useRecorder(options: RecorderOptions) {
  const [state, setState] = useState<RecorderState>('idle')
  const [level, setLevel] = useState(0)
  const [waveform, setWaveform] = useState<number[]>(new Array(72).fill(0))
  const [elapsed, setElapsed] = useState(0)
  const [partial, setPartial] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [upstream, setUpstream] = useState(false)
  const [connected, setConnected] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const optionsRef = useRef(options)
  optionsRef.current = options

  const ctxRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const nodeRef = useRef<AudioWorkletNode | ScriptProcessorNode | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef<number | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const chunksRef = useRef<Int16Array[]>([])
  const startedAtRef = useRef(0)
  const timerRef = useRef<number | null>(null)
  const sampleRateRef = useRef(TARGET_RATE)
  const stopResolveRef = useRef<((r: SpeechResult | null) => void) | null>(null)
  const finalRef = useRef<SpeechResult | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const cleanupAudio = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    if (timerRef.current) window.clearInterval(timerRef.current)
    timerRef.current = null
    try {
      nodeRef.current?.disconnect()
      sourceRef.current?.disconnect()
      analyserRef.current?.disconnect()
    } catch {
      /* already disconnected */
    }
    nodeRef.current = null
    sourceRef.current = null
    analyserRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    void ctxRef.current?.close().catch(() => undefined)
    ctxRef.current = null
  }, [])

  const closeSocket = useCallback(() => {
    const ws = wsRef.current
    wsRef.current = null
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      try {
        ws.close()
      } catch {
        /* noop */
      }
    }
    setConnected(false)
    setUpstream(false)
  }, [])

  useEffect(() => () => {
    cleanupAudio()
    closeSocket()
  }, [cleanupAudio, closeSocket])

  const fail = useCallback((message: string) => {
    setError(message)
    setState('error')
    optionsRef.current.onError?.(message)
  }, [])

  const sendControl = useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload))
  }, [])

  const startMeter = useCallback((analyser: AnalyserNode) => {
    const data = new Float32Array(analyser.fftSize)
    const tick = () => {
      analyser.getFloatTimeDomainData(data)
      let sum = 0
      for (let i = 0; i < data.length; i++) sum += data[i] * data[i]
      const rms = Math.sqrt(sum / data.length)
      const scaled = Math.min(1, rms * 3.4)
      if (mountedRef.current) {
        setLevel(scaled)
        setWaveform((prev) => {
          const next = prev.slice(1)
          next.push(scaled)
          return next
        })
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const handleSocketMessage = useCallback((raw: MessageEvent<string>) => {
    let msg: Record<string, unknown>
    try {
      msg = JSON.parse(raw.data) as Record<string, unknown>
    } catch {
      return
    }
    switch (msg.type) {
      case 'ready':
        setUpstream(Boolean(msg.upstream))
        setConnected(true)
        break
      case 'partial':
        if (typeof msg.text === 'string') {
          setPartial(msg.text)
          optionsRef.current.onPartial?.(msg.text)
        }
        break
      case 'notice':
        if (typeof msg.message === 'string') {
          setNotice(msg.message)
          optionsRef.current.onNotice?.(msg.message)
        }
        break
      case 'final': {
        const result = msg.transcription as SpeechResult | undefined
        if (result) {
          finalRef.current = result
          stopResolveRef.current?.(result)
          if (mountedRef.current) {
            setState('done')
            optionsRef.current.onFinal?.(result)
          }
        }
        break
      }
      case 'error':
        if (typeof msg.message === 'string') {
          fail(msg.message)
          stopResolveRef.current?.(null)
        }
        break
      default:
        break
    }
  }, [fail])

  const start = useCallback(async () => {
    if (state === 'recording' || state === 'requesting') return
    setError(null)
    setPartial('')
    setNotice(null)
    setElapsed(0)
    setWaveform(new Array(72).fill(0))
    finalRef.current = null
    chunksRef.current = []
    setState('requesting')

    if (!navigator.mediaDevices?.getUserMedia) {
      fail('This browser does not expose microphone access (getUserMedia). Try Chrome, Edge or Firefox on HTTPS or localhost.')
      return
    }

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
    } catch (err) {
      const name = (err as DOMException)?.name
      if (name === 'NotAllowedError' || name === 'SecurityError') {
        fail('Microphone permission was denied. Allow microphone access in the browser site settings and try again.')
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        fail('No microphone was found. Connect a microphone and try again.')
      } else if (name === 'NotReadableError') {
        fail('The microphone is busy in another application.')
      } else {
        fail(`Could not start the microphone: ${(err as Error).message ?? 'unknown error'}`)
      }
      return
    }
    streamRef.current = stream

    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const ctx = new AudioCtx({ sampleRate: TARGET_RATE })
      ctxRef.current = ctx
      sampleRateRef.current = ctx.sampleRate
      await ctx.resume().catch(() => undefined)

      const source = ctx.createMediaStreamSource(stream)
      sourceRef.current = source

      const analyser = ctx.createAnalyser()
      analyser.fftSize = 1024
      analyser.smoothingTimeConstant = 0.65
      source.connect(analyser)
      analyserRef.current = analyser
      startMeter(analyser)

      const pushSamples = (input: Float32Array) => {
        const down = downsample(input, ctx.sampleRate, TARGET_RATE)
        const pcm = toInt16(down)
        chunksRef.current.push(pcm)
        const ws = wsRef.current
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(pcm.buffer)
        }
      }

      let node: AudioWorkletNode | ScriptProcessorNode | null = null
      try {
        const blobUrl = URL.createObjectURL(new Blob([WORKLET_SOURCE], { type: 'application/javascript' }))
        await ctx.audioWorklet.addModule(blobUrl)
        URL.revokeObjectURL(blobUrl)
        const worklet = new AudioWorkletNode(ctx, 'pcm-capture')
        worklet.port.onmessage = (event: MessageEvent<Float32Array>) => pushSamples(event.data)
        node = worklet
      } catch {
        // Safari/older browsers: ScriptProcessor is deprecated but works
        const processor = ctx.createScriptProcessor(4096, 1, 1)
        processor.onaudioprocess = (event) => pushSamples(event.inputBuffer.getChannelData(0))
        node = processor
      }
      source.connect(node)
      // keep the graph alive without echoing to speakers
      const silent = ctx.createGain()
      silent.gain.value = 0
      node.connect(silent)
      silent.connect(ctx.destination)
      nodeRef.current = node

      // --- live transport ---
      const token = tokenStore.access
      if (token) {
        try {
          const ws = new WebSocket(liveSocketUrl(token))
          ws.binaryType = 'arraybuffer'
          wsRef.current = ws
          await new Promise<void>((resolve) => {
            const timeout = window.setTimeout(() => resolve(), 3500)
            ws.onopen = () => {
              window.clearTimeout(timeout)
              ws.send(
                JSON.stringify({
                  type: 'start',
                  mode: optionsRef.current.mode,
                  context: optionsRef.current.context,
                  language_code: optionsRef.current.languageCode,
                  include_outputs: optionsRef.current.includeOutputs,
                  noise_reduction: optionsRef.current.noiseReduction,
                  retain_audio: Boolean(optionsRef.current.retainAudio),
                  sample_rate: TARGET_RATE,
                  streaming: true,
                }),
              )
              resolve()
            }
            ws.onerror = () => {
              window.clearTimeout(timeout)
              resolve()
            }
          })
          ws.onmessage = handleSocketMessage
          ws.onclose = () => {
            setConnected(false)
            setUpstream(false)
          }
        } catch {
          setNotice('Live socket unavailable - the recording will be uploaded when you stop.')
        }
      }

      startedAtRef.current = performance.now()
      setState('recording')
      timerRef.current = window.setInterval(() => {
        const secs = (performance.now() - startedAtRef.current) / 1000
        setElapsed(secs)
        const max = optionsRef.current.maxSeconds ?? 300
        if (secs >= max) void stopRef.current?.()
      }, 200)
    } catch (err) {
      cleanupAudio()
      fail(`Audio pipeline failed: ${(err as Error).message ?? 'unknown error'}`)
    }
  }, [cleanupAudio, fail, handleSocketMessage, startMeter, state])

  const stop = useCallback(async (): Promise<SpeechResult | null> => {
    if (state !== 'recording') return null
    setState('stopping')
    if (timerRef.current) window.clearInterval(timerRef.current)
    timerRef.current = null
    cleanupAudio()

    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      setState('processing')
      const done = new Promise<SpeechResult | null>((resolve) => {
        stopResolveRef.current = resolve
        window.setTimeout(() => resolve(finalRef.current), 45000)
      })
      sendControl({ type: 'stop' })
      const result = await done
      closeSocket()
      if (!result) {
        setState('error')
        if (!error) setError('The server did not return a transcript. Check the backend logs.')
      }
      return result
    }

    // --- REST fallback: no socket, upload the buffered PCM as WAV ---
    closeSocket()
    const chunks = chunksRef.current
    if (!chunks.length) {
      setState('idle')
      return null
    }
    setState('processing')
    try {
      const wav = buildWav(chunks, TARGET_RATE)
      const result = await api.transcribe(wav, {
        mode: optionsRef.current.mode,
        context: optionsRef.current.context,
        language_code: optionsRef.current.languageCode ?? '',
        include_outputs: optionsRef.current.includeOutputs.join(','),
        noise_reduction: String(optionsRef.current.noiseReduction),
        retain_audio: String(Boolean(optionsRef.current.retainAudio)),
      })
      finalRef.current = result
      setState('done')
      optionsRef.current.onFinal?.(result)
      return result
    } catch (err) {
      fail(err instanceof Error ? err.message : 'Upload failed')
      return null
    }
  }, [cleanupAudio, closeSocket, error, fail, sendControl, state])

  const stopRef = useRef(stop)
  stopRef.current = stop

  const cancel = useCallback(() => {
    sendControl({ type: 'cancel' })
    cleanupAudio()
    closeSocket()
    chunksRef.current = []
    setState('idle')
    setPartial('')
    setElapsed(0)
    setLevel(0)
    setWaveform(new Array(72).fill(0))
  }, [cleanupAudio, closeSocket, sendControl])

  const reset = useCallback(() => {
    setState('idle')
    setPartial('')
    setError(null)
    setNotice(null)
    setElapsed(0)
    setLevel(0)
    setWaveform(new Array(72).fill(0))
  }, [])

  return {
    state,
    level,
    waveform,
    elapsed,
    partial,
    error,
    notice,
    upstream,
    connected,
    start,
    stop,
    cancel,
    reset,
  }
}
