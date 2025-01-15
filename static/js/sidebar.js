var isSidebarOpen = false; // Track the state of the sidebar

function toggleNav() {
    const sidenav = document.getElementById("mySidenav");

    if (isSidebarOpen) {
        // Close the sidebar
        sidenav.style.width = "0";
        isSidebarOpen = false; // Update state
        document.removeEventListener("click", closeOnOutsideClick); // Remove event listener
    } else {
        // Open the sidebar
        if (window.matchMedia("(max-width: 575.98px)").matches) sidenav.style.width = "200px";
        else sidenav.style.width = "300px";
        
        isSidebarOpen = true; // Update state
        document.addEventListener("click", closeOnOutsideClick); // Add event listener
    }
}

function closeOnOutsideClick(event) {
    const sidenav = document.getElementById("mySidenav");
    const openButton = document.querySelector(".openbtn-sidenav");

    // Check if the click was outside the sidebar and not on the button
    if (!sidenav.contains(event.target) && event.target !== openButton) {
        toggleNav(); // Close the sidebar
    }
}