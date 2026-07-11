document.addEventListener("DOMContentLoaded", function () {

    console.log("DOM Loaded");

    const profileBtn = document.getElementById("profileBtn");
    const profileMenu = document.getElementById("profileMenu");

    console.log(profileBtn);
    console.log(profileMenu);

    if (profileBtn && profileMenu) {

        profileBtn.addEventListener("click", function (e) {
            console.log("Button clicked");
            e.stopPropagation();
            profileMenu.classList.toggle("hidden");
        });

        document.addEventListener("click", function (e) {
            if (!profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
                profileMenu.classList.add("hidden");
            }
        });

    } else {
        console.log("Elements not found");
    }

});