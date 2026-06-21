const catalog = JSON.parse(document.querySelector("#catalogData").textContent);

const state = {
  worlds: new Set(["princesses", "unicorns"]),
  characters: new Set(["princess", "unicorn"]),
  action: "riding",
  orientation: "portrait",
  current: null,
  pollTimer: null,
};

const elements = {
  builderView: document.querySelector("#builderView"),
  resultView: document.querySelector("#resultView"),
  form: document.querySelector("#generationForm"),
  error: document.querySelector("#formError"),
  generateButton: document.querySelector("#generateButton"),
  loading: document.querySelector("#loadingOverlay"),
  status: document.querySelector("#appStatus span:last-child"),
  idea: document.querySelector("#customIdea"),
  ideaCount: document.querySelector("#ideaCount"),
  selectionHint: document.querySelector("#selectionHint"),
  paperFrame: document.querySelector("#paperFrame"),
  resultImage: document.querySelector("#resultImage"),
  resultSummary: document.querySelector("#resultSummary"),
  printButton: document.querySelector("#printButton"),
  patternPrintButton: document.querySelector("#patternPrintButton"),
  pngButton: document.querySelector("#pngButton"),
  colorButton: document.querySelector("#colorButton"),
  pdfButton: document.querySelector("#pdfButton"),
  recentSection: document.querySelector("#recentSection"),
  recentRail: document.querySelector("#recentRail"),
};

const setSelected = (element, selected) => {
  element.classList.toggle("selected", selected);
  element.setAttribute("aria-pressed", String(selected));
};

document.querySelectorAll("[data-world-id].world-card").forEach((button) => {
  button.addEventListener("click", () => {
    const worldId = button.dataset.worldId;
    if (state.worlds.has(worldId)) {
      if (state.worlds.size === 1) return;
      state.worlds.delete(worldId);
      catalog.characters
        .filter((character) => character.world_id === worldId)
        .forEach((character) => state.characters.delete(character.id));
    } else {
      state.worlds.add(worldId);
    }
    syncSelections();
  });
});

document.querySelectorAll("[data-character-id]").forEach((button) => {
  button.addEventListener("click", () => {
    const characterId = button.dataset.characterId;
    if (state.characters.has(characterId)) {
      if (state.characters.size === 1) return;
      state.characters.delete(characterId);
    } else {
      if (state.characters.size >= 4) {
        elements.selectionHint.textContent = "Vybrať sa dajú najviac 4 postavy.";
        elements.selectionHint.style.color = "#b43b3b";
        return;
      }
      state.characters.add(characterId);
      state.worlds.add(button.dataset.worldId);
    }
    elements.selectionHint.textContent = "Môžeš vybrať najviac 4 postavy.";
    elements.selectionHint.style.color = "";
    syncSelections();
  });
});

document.querySelectorAll("[data-action-id]").forEach((button) => {
  button.addEventListener("click", () => {
    state.action = button.dataset.actionId;
    document.querySelectorAll("[data-action-id]").forEach((candidate) => {
      setSelected(candidate, candidate === button);
    });
  });
});

document.querySelectorAll("[data-orientation]").forEach((button) => {
  button.addEventListener("click", () => {
    state.orientation = button.dataset.orientation;
    document.querySelectorAll("[data-orientation]").forEach((candidate) => {
      setSelected(candidate, candidate === button);
    });
  });
});

elements.idea.addEventListener("input", () => {
  elements.ideaCount.textContent = String(elements.idea.value.length);
});

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await createGeneration();
});

document.querySelector("#editButton").addEventListener("click", showBuilder);
document.querySelector("#similarButton").addEventListener("click", showBuilder);
document.querySelector("#retryButton").addEventListener("click", createGeneration);

const syncSelections = () => {
  document.querySelectorAll(".world-card").forEach((button) => {
    setSelected(button, state.worlds.has(button.dataset.worldId));
  });
  document.querySelectorAll(".character-card").forEach((button) => {
    setSelected(button, state.characters.has(button.dataset.characterId));
  });
};

const requestPayload = () => ({
  worlds: [...state.worlds],
  characters: [...state.characters],
  action: state.action,
  custom_idea: elements.idea.value.trim(),
  orientation: state.orientation,
});

async function createGeneration() {
  clearError();
  setLoading(true);
  try {
    const response = await fetch("/api/generations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload()),
    });
    const data = await response.json();
    if (!response.ok) {
      const message = data.detail?.message || data.detail || "Generovanie sa nepodarilo spustiť.";
      throw new Error(message);
    }
    await pollGeneration(data.id);
  } catch (error) {
    setLoading(false);
    showBuilder();
    showError(error.message);
  }
}

async function pollGeneration(generationId) {
  clearTimeout(state.pollTimer);
  const response = await fetch(`/api/generations/${generationId}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Stav generovania sa nepodarilo načítať.");
  if (data.status === "done") {
    setLoading(false);
    await showResult(data);
    return;
  }
  if (data.status === "failed") {
    throw new Error(data.error || "Generovanie zlyhalo.");
  }
  state.pollTimer = setTimeout(() => pollGeneration(generationId), 1200);
}

async function showResult(item) {
  state.current = item;
  elements.builderView.hidden = true;
  elements.resultView.hidden = false;
  elements.status.textContent = "Omaľovánka je hotová";
  elements.resultImage.src = `${item.png_url}?v=${Date.now()}`;
  elements.paperFrame.className = `paper-frame ${item.request.orientation}`;
  elements.printButton.href = item.print_url;
  elements.patternPrintButton.href = item.pattern_print_url || item.print_url;
  elements.pngButton.href = item.png_url;
  elements.colorButton.href = item.color_url;
  elements.pdfButton.href = item.pdf_url;

  const labels = item.request.characters
    .map((id) => catalog.characters.find((character) => character.id === id)?.label)
    .filter(Boolean);
  const orientation = item.request.orientation === "portrait" ? "na výšku" : "na šírku";
  elements.resultSummary.textContent = `${labels.join(" + ")} • ${orientation} • pre deti 3–5 rokov`;
  window.scrollTo({ top: 0, behavior: "smooth" });
  await loadRecent(item.id);
}

function showBuilder() {
  clearTimeout(state.pollTimer);
  elements.resultView.hidden = true;
  elements.builderView.hidden = false;
  elements.status.textContent = "Pripravené na tvorenie";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function loadRecent(selectedId = null) {
  try {
    const response = await fetch("/api/colorings?limit=20");
    if (!response.ok) return;
    const items = await response.json();
    elements.recentRail.replaceChildren();
    items.slice(0, 6).forEach((item) => {
      const button = document.createElement("button");
      button.className = `recent-item ${item.id === selectedId ? "selected" : ""}`;
      button.type = "button";
      button.setAttribute("aria-label", `Otvoriť omaľovánku ${item.id}`);
      const image = document.createElement("img");
      image.src = item.png_url;
      image.alt = "";
      button.append(image);
      button.addEventListener("click", () => showResult(item));
      elements.recentRail.append(button);
    });
    elements.recentSection.hidden = items.length === 0;
  } catch {
    elements.recentSection.hidden = true;
  }
}

function setLoading(loading) {
  elements.loading.hidden = !loading;
  elements.generateButton.disabled = loading;
  elements.status.textContent = loading ? "Kreslíme omaľovánku…" : "Pripravené na tvorenie";
}

function showError(message) {
  elements.error.textContent = message;
  elements.error.hidden = false;
}

function clearError() {
  elements.error.hidden = true;
  elements.error.textContent = "";
}

syncSelections();
loadRecent();
