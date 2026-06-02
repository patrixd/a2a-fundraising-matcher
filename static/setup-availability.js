(function () {
  const list = document.getElementById("availability-list");
  const jsonInput = document.getElementById("availability_json");
  const addBtn = document.getElementById("add-slot-btn");
  const initialEl = document.getElementById("availability-initial");
  if (!list || !jsonInput || !addBtn) return;

  const dateInput = document.getElementById("new_slot_date");
  const startInput = document.getElementById("new_slot_start");
  const endInput = document.getElementById("new_slot_end");

  /** YYYY-MM-DD in local timezone (avoid UTC shift from toISOString). */
  function localDateString(d) {
    const x = d || new Date();
    const y = x.getFullYear();
    const m = String(x.getMonth() + 1).padStart(2, "0");
    const day = String(x.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  /** Normalize <input type="time"> → HH:MM (Safari may send HH:MM:SS). */
  function normalizeTime(t) {
    if (!t) return "";
    const parts = String(t).trim().split(":");
    if (parts.length < 2) return "";
    const h = parts[0].padStart(2, "0");
    const m = parts[1].padStart(2, "0");
    return `${h}:${m}`;
  }

  function parseTimeToMinutes(t) {
    const n = normalizeTime(t);
    if (!n) return NaN;
    const [h, m] = n.split(":").map(Number);
    return h * 60 + m;
  }

  function formatTime12(t) {
    const n = normalizeTime(t);
    if (!n) return t;
    const [h, m] = n.split(":").map(Number);
    const ampm = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 || 12;
    return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
  }

  function formatDateDisplay(isoDate) {
    if (!isoDate) return isoDate;
    const [y, mo, d] = isoDate.split("-").map(Number);
    const dt = new Date(y, mo - 1, d);
    if (Number.isNaN(dt.getTime())) return isoDate;
    return dt.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatSlotLabel(s) {
    return `${formatDateDisplay(s.slot_date)} · ${formatTime12(s.start_time)} – ${formatTime12(s.end_time)}`;
  }

  function normalizeSlot(raw) {
    return {
      slot_date: (raw.slot_date || "").trim(),
      start_time: normalizeTime(raw.start_time),
      end_time: normalizeTime(raw.end_time),
    };
  }

  let slots = [];
  try {
    const initial = initialEl ? JSON.parse(initialEl.textContent || "[]") : [];
    slots = Array.isArray(initial)
      ? initial.map(normalizeSlot).filter((s) => s.slot_date && s.start_time && s.end_time)
      : [];
  } catch (_) {
    slots = [];
  }

  function render() {
    list.innerHTML = "";
    if (!slots.length) {
      list.innerHTML =
        '<li class="avail-empty">No slots yet — add dates you’re free for an intro call.</li>';
    } else {
      slots.forEach((s, i) => {
        const li = document.createElement("li");
        li.className = "avail-item";
        const label = document.createElement("span");
        label.className = "avail-when";
        label.textContent = formatSlotLabel(s);
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-ghost btn-sm avail-remove";
        btn.dataset.i = String(i);
        btn.textContent = "Remove";
        li.appendChild(label);
        li.appendChild(btn);
        list.appendChild(li);
      });
    }
    jsonInput.value = JSON.stringify(slots);
  }

  function defaultDate() {
    const d = new Date();
    d.setDate(d.getDate() + 3);
    while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
    return localDateString(d);
  }

  if (dateInput && !dateInput.value) dateInput.value = defaultDate();
  if (startInput && !startInput.value) startInput.value = "14:00";
  if (endInput && !endInput.value) endInput.value = "16:00";

  addBtn.addEventListener("click", () => {
    const slot = normalizeSlot({
      slot_date: dateInput.value,
      start_time: startInput.value,
      end_time: endInput.value,
    });

    if (!slot.slot_date || !slot.start_time || !slot.end_time) {
      alert("Please choose a date and both times.");
      return;
    }

    const startM = parseTimeToMinutes(slot.start_time);
    const endM = parseTimeToMinutes(slot.end_time);
    if (endM <= startM) {
      alert("End time must be after start time.");
      return;
    }

    slots.push(slot);
    slots.sort((a, b) =>
      `${a.slot_date}T${a.start_time}`.localeCompare(`${b.slot_date}T${b.start_time}`)
    );
    render();
  });

  list.addEventListener("click", (e) => {
    const btn = e.target.closest(".avail-remove");
    if (!btn) return;
    slots.splice(Number(btn.dataset.i), 1);
    render();
  });

  document.querySelector(".setup-form")?.addEventListener("submit", () => {
    jsonInput.value = JSON.stringify(slots);
  });

  render();
})();
