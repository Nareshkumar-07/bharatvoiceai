// BharatVoice AI - Tauri desktop shell.
//
// Real behaviour:
//   * global shortcut registration (works while other apps are focused)
//   * show/hide of a floating always-on-top microphone window
//   * copy-to-clipboard of the last transcript, then a synthetic paste
//
// Honest limits (see docs/desktop.md):
//   * synthetic paste needs Accessibility permission on macOS and is generally
//     blocked on Wayland;
//   * the transcription itself is produced by the same backend the web app uses.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_clipboard_manager::ClipboardExt;
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

const TOGGLE_ACCELERATOR: (Modifiers, Code) = (Modifiers::CONTROL | Modifiers::SHIFT, Code::Space);
const COPY_ACCELERATOR: (Modifiers, Code) = (Modifiers::CONTROL | Modifiers::SHIFT, Code::KeyC);

#[tauri::command]
fn copy_transcript(app: tauri::AppHandle, text: String) -> Result<(), String> {
    app.clipboard()
        .write_text(text)
        .map_err(|e| format!("clipboard error: {e}"))
}

#[tauri::command]
fn show_floating_mic(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("floating-mic") {
        window.show().map_err(|e| e.to_string())?;
        window.set_focus().map_err(|e| e.to_string())?;
        return Ok(());
    }
    WebviewWindowBuilder::new(&app, "floating-mic", WebviewUrl::App("index.html#/app/workspace".into()))
        .title("BharatVoice")
        .inner_size(380.0, 190.0)
        .always_on_top(true)
        .decorations(false)
        .transparent(true)
        .skip_taskbar(true)
        .build()
        .map_err(|e| e.to_string())?;
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, shortcut, event| {
                    if event.state() != ShortcutState::Pressed {
                        return;
                    }
                    let toggle = Shortcut::new(Some(TOGGLE_ACCELERATOR.0), TOGGLE_ACCELERATOR.1);
                    let copy = Shortcut::new(Some(COPY_ACCELERATOR.0), COPY_ACCELERATOR.1);
                    if shortcut == &toggle {
                        // Ask the frontend to start/stop; it owns the recorder state.
                        if let Some(window) = app.get_webview_window("floating-mic") {
                            let _ = window.show();
                        }
                        if let Some(main) = app.get_webview_window("main") {
                            let _ = main.emit("bharatvoice://toggle-recording", ());
                        }
                    } else if shortcut == &copy {
                        if let Some(main) = app.get_webview_window("main") {
                            let _ = main.emit("bharatvoice://copy-last", ());
                        }
                    }
                })
                .build(),
        )
        .invoke_handler(tauri::generate_handler![copy_transcript, show_floating_mic])
        .setup(|app| {
            let gs = app.global_shortcut();
            gs.register(Shortcut::new(Some(TOGGLE_ACCELERATOR.0), TOGGLE_ACCELERATOR.1))?;
            gs.register(Shortcut::new(Some(COPY_ACCELERATOR.0), COPY_ACCELERATOR.1))?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running BharatVoice desktop shell");
}
