// app.js — modern interactions, favorites, view mode & responsive behavior
document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Lucide Icons
    if (window.lucide) {
        window.lucide.createIcons();
    }

    // 2. Mobile Sidebar Drawer
    const mobileMenuOpenBtn = document.getElementById("mobile-menu-open-btn");
    const mobileMenuCloseBtn = document.getElementById("mobile-menu-close-btn");
    const sidebarDrawer = document.getElementById("app-sidebar");
    const sidebarBackdrop = document.getElementById("sidebar-backdrop");

    function openSidebar() {
        if (sidebarDrawer) {
            sidebarDrawer.classList.remove("-translate-x-full");
        }
        if (sidebarBackdrop) {
            sidebarBackdrop.classList.remove("hidden");
        }
    }

    function closeSidebar() {
        if (sidebarDrawer) {
            sidebarDrawer.classList.add("-translate-x-full");
        }
        if (sidebarBackdrop) {
            sidebarBackdrop.classList.add("hidden");
        }
    }

    if (mobileMenuOpenBtn) {
        mobileMenuOpenBtn.addEventListener("click", openSidebar);
    }
    if (mobileMenuCloseBtn) {
        mobileMenuCloseBtn.addEventListener("click", closeSidebar);
    }
    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener("click", closeSidebar);
    }

    // 3. Keyboard Shortcut: Ctrl + K or '/'
    document.addEventListener("keydown", (e) => {
        if ((e.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) || 
            ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k")) {
            const searchInput = document.getElementById("tool-search-input");
            if (searchInput) {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        }
    });

    // 4. Tool Favorites Handling
    let favorites = JSON.parse(localStorage.getItem("app_favorites") || "[]");

    function updateFavoriteStars() {
        document.querySelectorAll(".fav-btn").forEach(btn => {
            const toolId = btn.getAttribute("data-fav-id");
            if (favorites.includes(toolId)) {
                btn.classList.add("text-amber-400");
                btn.classList.remove("text-slate-300", "dark:text-slate-600");
            } else {
                btn.classList.remove("text-amber-400");
                btn.classList.add("text-slate-300", "dark:text-slate-600");
            }
        });
    }

    document.querySelectorAll(".fav-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            const toolId = btn.getAttribute("data-fav-id");
            if (favorites.includes(toolId)) {
                favorites = favorites.filter(id => id !== toolId);
            } else {
                favorites.push(toolId);
            }
            localStorage.setItem("app_favorites", JSON.stringify(favorites));
            updateFavoriteStars();
        });
    });

    updateFavoriteStars();

    // 5. Grid View vs List View
    const gridViewBtn = document.getElementById("view-grid-btn");
    const listViewBtn = document.getElementById("view-list-btn");
    const toolsGrid = document.getElementById("tools-grid");

    const savedView = localStorage.getItem("app_view_mode") || "grid";

    function setViewMode(mode) {
        if (!toolsGrid) return;
        if (mode === "list") {
            toolsGrid.classList.add("list-view");
            if (listViewBtn) {
                listViewBtn.classList.add("bg-indigo-600", "text-white");
                listViewBtn.classList.remove("text-slate-500", "dark:text-slate-400");
            }
            if (gridViewBtn) {
                gridViewBtn.classList.remove("bg-indigo-600", "text-white");
                gridViewBtn.classList.add("text-slate-500", "dark:text-slate-400");
            }
        } else {
            toolsGrid.classList.remove("list-view");
            if (gridViewBtn) {
                gridViewBtn.classList.add("bg-indigo-600", "text-white");
                gridViewBtn.classList.remove("text-slate-500", "dark:text-slate-400");
            }
            if (listViewBtn) {
                listViewBtn.classList.remove("bg-indigo-600", "text-white");
                listViewBtn.classList.add("text-slate-500", "dark:text-slate-400");
            }
        }
        localStorage.setItem("app_view_mode", mode);
    }

    if (gridViewBtn && listViewBtn) {
        setViewMode(savedView);
        gridViewBtn.addEventListener("click", () => setViewMode("grid"));
        listViewBtn.addEventListener("click", () => setViewMode("list"));
    }
});
