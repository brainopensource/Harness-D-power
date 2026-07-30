// FE-1: blank shell only, no commands wired yet — those land as RunClient/EventSource
// integration grows in FE-2 onward.
fn main() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
