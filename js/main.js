(function () {
  var levelButtons = document.querySelectorAll("[data-level]");
  var formButtons = document.querySelectorAll("[data-form]");
  var facultyLinks = document.querySelectorAll("[data-faculty]");
  var forms = document.getElementById("forms");
  var faculties = document.getElementById("faculties");
  var level = null;
  var form = null;

  function writeLinks() {
    if (!level || !form) return;
    facultyLinks.forEach(function (link) {
      var faculty = link.getAttribute("data-faculty");
      link.href = "schedule.html?level=" + encodeURIComponent(level) +
        "&form=" + encodeURIComponent(form) +
        "&faculty=" + encodeURIComponent(faculty);
    });
  }

  levelButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      level = button.getAttribute("data-level");
      levelButtons.forEach(function (item) {
        var selected = item === button;
        item.classList.toggle("is-selected", selected);
        item.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      forms.hidden = false;
      writeLinks();
      forms.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });

  formButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      form = button.getAttribute("data-form");
      formButtons.forEach(function (item) {
        var selected = item === button;
        item.classList.toggle("is-selected", selected);
        item.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      writeLinks();
      faculties.hidden = false;
      faculties.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
})();
