(function () {
  var LEVELS = {
    bachelor: "Бакалавриат/Специалитет",
    master: "Магистратура"
  };
  var FORMS = {
    fulltime: "Очная форма",
    mixed: "Очно-заочная форма",
    distance: "Заочная форма"
  };
  var FACULTIES = {
    feeiu: "ФЭЭиУ",
    gtf: "ГТФ"
  };
  var DAYS = [
    ["mon", "Понедельник"],
    ["tue", "Вторник"],
    ["wed", "Среда"],
    ["thu", "Четверг"],
    ["fri", "Пятница"],
    ["sat", "Суббота"]
  ];

  var params = new URLSearchParams(location.search);
  var level = params.get("level");
  var form = params.get("form");
  var data = window.SCHEDULE;
  var gate = document.getElementById("gate");
  var board = document.getElementById("board");
  var broken = document.getElementById("broken");

  if (!data || !Array.isArray(data.groups)) {
    broken.hidden = false;
    return;
  }

  if (!LEVELS[level] || !FORMS[form]) {
    gate.hidden = false;
    return;
  }

  board.hidden = false;

  var download = document.getElementById("download-link");
  var excelLink = document.getElementById("excel-link");
  var filePath = data.downloads && data.downloads[level] && data.downloads[level][form];
  if (filePath) {
    var fileUrl = new URL(filePath, document.baseURI).href;
    var fileName = filePath.split("/").pop();
    download.href = fileUrl;
    download.setAttribute("download", fileName);
    download.hidden = false;
    if (excelLink) {
      excelLink.href = fileUrl;
      excelLink.setAttribute("download", fileName);
    }
  }

  var courseMenu = document.getElementById("course-menu");
  var tableWrap = document.getElementById("table-wrap");
  var emptyNote = document.getElementById("empty-note");
  var weekSwitch = document.getElementById("week-switch");
  var weekDate = document.getElementById("week-date");
  var weekCount = document.getElementById("week-count");
  var oddLabel = document.getElementById("odd-label");
  var evenLabel = document.getElementById("even-label");
  var selectedCourse = null;
  var selectedParity = "odd";
  var viewedWeek = null;
  var calendar = null;
  var weekPrev = document.getElementById("week-prev");
  var weekNext = document.getElementById("week-next");
  var facultyTabs = document.querySelectorAll(".faculty-tab");
  var slice = [];
  var courses = [];
  var selectedFaculty = null;

  courseMenu.addEventListener("click", function (event) {
    var option = event.target.closest(".course-option");
    if (!option) return;
    chooseCourse(Number(option.getAttribute("data-course")));
  });

  weekSwitch.addEventListener("click", function () {
    showWeek(viewedWeek + (selectedParity === "even" ? -1 : 1));
  });
  weekPrev.addEventListener("click", function () { showWeek(viewedWeek - 1); });
  weekNext.addEventListener("click", function () { showWeek(viewedWeek + 1); });

  var today = krasnoyarskDate();
  publishDate(today.year, today.month, today.day);

  facultyTabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      selectFaculty(tab.getAttribute("data-faculty"), true);
    });
  });

  selectFaculty(params.get("faculty"), false);

  function groupsOf(faculty) {
    return data.groups.filter(function (group) {
      return group.level === level && group.form === form && group.faculty === faculty;
    });
  }

  function selectFaculty(faculty, keepCourse) {
    if (!FACULTIES[faculty] || !groupsOf(faculty).length) {
      faculty = groupsOf("feeiu").length ? "feeiu" : "gtf";
    }
    selectedFaculty = faculty;
    slice = groupsOf(faculty);
    facultyTabs.forEach(function (tab) {
      var selected = tab.getAttribute("data-faculty") === faculty;
      tab.classList.toggle("is-selected", selected);
      tab.setAttribute("aria-selected", selected ? "true" : "false");
    });
    document.title = FACULTIES[faculty] + ", " + LEVELS[level] + ", " + FORMS[form] + " - расписание";
    document.getElementById("board-title").textContent = FACULTIES[faculty] + " · " + LEVELS[level] + " · " + FORMS[form];
    var url = new URL(location.href);
    url.searchParams.set("faculty", faculty);

    var presentCourses = slice.map(function (group) { return Number(group.course); }).filter(function (course, index, list) {
      return Number.isInteger(course) && course > 0 && list.indexOf(course) === index;
    }).sort(function (a, b) { return a - b; });
    courses = presentCourses;
    if (level === "bachelor") {
      var maxCourse = 6;
      presentCourses.forEach(function (course) {
        if (course > maxCourse) maxCourse = course;
      });
      courses = [];
      for (var courseNumber = 1; courseNumber <= maxCourse; courseNumber += 1) courses.push(courseNumber);
    }
    courseMenu.innerHTML = courses.map(function (course) {
      return '<button type="button" class="course-option" data-course="' + course + '" aria-pressed="false">' + course + " курс</button>";
    }).join("");

    if (!courses.length) {
      selectedCourse = null;
      tableWrap.hidden = true;
      tableWrap.innerHTML = "";
      emptyNote.hidden = false;
      emptyNote.textContent = "Для этого факультета группы ещё не добавлены.";
      history.replaceState(null, "", url);
      return;
    }

    var next = null;
    if (keepCourse && courses.indexOf(selectedCourse) !== -1) next = selectedCourse;
    if (next === null && !keepCourse && courses.indexOf(Number(params.get("course"))) !== -1) {
      next = Number(params.get("course"));
    }
    if (next === null) {
      next = courses.filter(function (course) {
        return slice.some(function (group) { return Number(group.course) === course; });
      })[0];
    }
    if (next) {
      url.searchParams.set("course", String(next));
      history.replaceState(null, "", url);
      chooseCourse(next);
    }
  }

  function chooseCourse(course) {
    selectedCourse = course;
    courseMenu.querySelectorAll(".course-option").forEach(function (option) {
      var selected = Number(option.getAttribute("data-course")) === course;
      option.classList.toggle("is-selected", selected);
      option.setAttribute("aria-pressed", selected ? "true" : "false");
    });
    var url = new URL(location.href);
    url.searchParams.set("course", String(course));
    history.replaceState(null, "", url);
    renderTable();
  }

  function showWeek(weekNo) {
    if (weekNo < 1) weekNo = 1;
    if (weekNo > 42) weekNo = 42;
    viewedWeek = weekNo;
    selectedParity = weekNo % 2 === 0 ? "even" : "odd";
    var even = selectedParity === "even";
    weekSwitch.setAttribute("aria-checked", even ? "true" : "false");
    weekSwitch.setAttribute("aria-label", even ? "Показана чётная неделя" : "Показана нечётная неделя");
    oddLabel.classList.toggle("is-active", !even);
    evenLabel.classList.toggle("is-active", even);
    updateNote();
    if (selectedCourse !== null) renderTable();
  }

  function publishDate(year, month, day) {
    var weekNo = studyWeekNumber(year, month, day);
    var dateLabel = new Intl.DateTimeFormat("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
      timeZone: "UTC"
    }).format(new Date(Date.UTC(year, month - 1, day)));
    calendar = {
      weekNo: weekNo,
      parity: weekNo % 2 === 0 ? "even" : "odd",
      dateLabel: dateLabel
    };
    showWeek(weekNo);
  }

  // updateNote ставит сегодняшнюю дату Красноярска и номер открытой учебной недели.
  function updateNote() {
    if (!calendar || viewedWeek === null) return;
    var parity = viewedWeek % 2 === 0 ? "чётная" : "нечётная";
    weekDate.textContent = calendar.dateLabel;
    weekCount.textContent = viewedWeek + "-я учебная неделя - " + parity;
  }

  function lessonVisible(lesson) {
    if (lesson.weeks && lesson.weeks.length) {
      return lesson.weeks.indexOf(viewedWeek) !== -1;
    }
    var week = lesson.week || "both";
    return week === "both" || week === selectedParity;
  }

  // renderTable рисует дни строками, группы - столбцами.
  function renderTable() {
    var groups = slice.filter(function (group) {
      return Number(group.course) === selectedCourse;
    }).sort(function (a, b) {
      return String(a.name).localeCompare(String(b.name), "ru");
    });

    if (!groups.length) {
      tableWrap.hidden = true;
      tableWrap.innerHTML = "";
      emptyNote.hidden = false;
      emptyNote.textContent = "На этом курсе групп нет.";
      return;
    }

    emptyNote.hidden = true;
    var head = groups.map(function (group) {
      var badge = group.demo ? '<span class="demo-badge">демо</span>' : "";
      return '<th scope="col">' + esc(group.name) + badge + "</th>";
    }).join("");
    var rows = DAYS.map(function (day) {
      var cells = groups.map(function (group) {
        var lessons = (group.days && group.days[day[0]] ? group.days[day[0]] : []).filter(lessonVisible).sort(function (a, b) {
          return (Number(a.pair) || 99) - (Number(b.pair) || 99);
        });
        if (!lessons.length) return '<td><span class="day-empty">-</span></td>';
        return "<td>" + lessons.map(renderLesson).join("") + "</td>";
      }).join("");
      return '<tr><th scope="row">' + day[1] + "</th>" + cells + "</tr>";
    }).join("");

    tableWrap.hidden = false;
    tableWrap.innerHTML = '<table class="schedule-table"><thead><tr><th scope="col">День</th>' + head + "</tr></thead><tbody>" + rows + "</tbody></table>";
  }

  function renderLesson(lesson) {
    var meta = [];
    if (lesson.pair) meta.push("<span>" + esc(lesson.pair) + " пара</span>");
    if (lesson.time) meta.push("<span>" + esc(lesson.time) + "</span>");
    if (lesson.week === "even") meta.push('<span class="week-tag">чётная</span>');
    if (lesson.week === "odd") meta.push('<span class="week-tag">нечётная</span>');
    var kindAttr = lesson.kind ? ' data-kind="' + esc(lesson.kind) + '"' : "";
    return '<article class="lesson"' + kindAttr + ">" +
      (meta.length ? '<p class="lesson-meta">' + meta.join("") + "</p>" : "") +
      (lesson.subject ? '<p class="lesson-subject">' + esc(lesson.subject) + "</p>" : "") +
      (lesson.kind ? '<p class="lesson-kind">' + esc(lesson.kind) + "</p>" : "") +
      (lesson.teacher ? '<p class="lesson-teacher">' + esc(lesson.teacher) + "</p>" : "") +
      (lesson.room ? '<p class="lesson-room">' + esc(lesson.room) + "</p>" : "") +
      (lesson.note ? '<p class="lesson-note">' + esc(lesson.note) + "</p>" : "") +
      "</article>";
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char];
    });
  }

  // studyWeekNumber считает учебную неделю от 1 сентября.
  // Неделя 1 - с 1 сентября до ближайшего воскресенья, дальше понедельник-воскресенье.
  // До 1 сентября берётся 1 сентября прошлого учебного года, в январе отсчёт не сбрасывается.
  function studyWeekNumber(year, month, day) {
    var startYear = month >= 9 ? year : year - 1;
    var start = new Date(Date.UTC(startYear, 8, 1));
    var startDow = start.getUTCDay() || 7;
    var week1Monday = new Date(start);
    week1Monday.setUTCDate(start.getUTCDate() - (startDow - 1));
    var date = new Date(Date.UTC(year, month - 1, day));
    var diff = Math.round((date - week1Monday) / 86400000);
    var week = Math.floor(diff / 7) + 1;
    return week < 1 ? 1 : week;
  }

  // krasnoyarskDate берёт календарную дату пояса Asia/Krasnoyarsk в браузере.
  // Пояс без летнего времени, запасной сдвиг +7 часов от UTC.
  function krasnoyarskDate() {
    try {
      var parts = new Intl.DateTimeFormat("en-US", {
        timeZone: "Asia/Krasnoyarsk",
        year: "numeric",
        month: "numeric",
        day: "numeric"
      }).formatToParts(new Date());
      var pick = {};
      parts.forEach(function (part) {
        if (part.type === "year" || part.type === "month" || part.type === "day") {
          pick[part.type] = Number(part.value);
        }
      });
      if (pick.year && pick.month && pick.day) return pick;
    } catch (error) {}
    var shifted = new Date(Date.now() + 7 * 60 * 60 * 1000);
    return {
      year: shifted.getUTCFullYear(),
      month: shifted.getUTCMonth() + 1,
      day: shifted.getUTCDate()
    };
  }
})();
