document.addEventListener("DOMContentLoaded", () => {
    const loadingOverlay = document.getElementById("loadingOverlay");
    const mainContent = document.getElementById("mainContent");

    // The CSS animation runs for 6s. We fade out at 6s.
    const FLIGHT_DURATION_MS = 6000;
    const FADE_DURATION_MS = 600;

    setTimeout(() => {
        if (loadingOverlay) {
            loadingOverlay.classList.add("fade-out");
        }

        if (mainContent) {
            mainContent.classList.add("visible");
        }

        // Clean up overlay from DOM layout after fade out
        setTimeout(() => {
            if (loadingOverlay) {
                loadingOverlay.style.display = "none";
            }
        }, FADE_DURATION_MS);
    }, FLIGHT_DURATION_MS);
});
