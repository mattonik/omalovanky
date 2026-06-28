const catalog = JSON.parse(document.querySelector("#catalogData").textContent);

const state = {
  worlds: new Set(["princesses", "unicorns"]),
  characters: new Set(),
  action: "riding",
  creationMode: "coloring",
  storyType: "trip",
  orientation: "portrait",
  generationMode: "line_art_direct",
  primaryMode: "line_art",
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
  comicIdea: document.querySelector("#comicIdea"),
  comicIdeaCount: document.querySelector("#comicIdeaCount"),
  selectionHint: document.querySelector("#selectionHint"),
  coloringOptions: document.querySelector("#coloringOptions"),
  comicOptions: document.querySelector("#comicOptions"),
  paperSetting: document.querySelector("#paperSetting"),
  renderSetting: document.querySelector("#renderSetting"),
  comicModeSetting: document.querySelector("#comicModeSetting"),
  generationEstimate: document.querySelector("#generationEstimate"),
  paperFrame: document.querySelector("#paperFrame"),
  resultImage: document.querySelector("#resultImage"),
  comicPages: document.querySelector("#comicPages"),
  resultSummary: document.querySelector("#resultSummary"),
  printButton: document.querySelector("#printButton"),
  patternPrintButton: document.querySelector("#patternPrintButton"),
  pngButton: document.querySelector("#pngButton"),
  colorButton: document.querySelector("#colorButton"),
  pdfButton: document.querySelector("#pdfButton"),
  comicColorPdfButton: document.querySelector("#comicColorPdfButton"),
  renderModeControl: document.querySelector("#renderModeControl"),
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
    elements.selectionHint.textContent = state.characters.size
      ? "Môžeš vybrať najviac 4 postavy. Nechať ich prázdne je tiež v poriadku."
      : "Postavy sú voliteľné. Môžeš nechať len tému.";
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

document.querySelectorAll("[data-creation-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    state.creationMode = button.dataset.creationMode;
    document.querySelectorAll("[data-creation-mode]").forEach((candidate) => {
      setSelected(candidate, candidate === button);
    });
    syncCreationMode();
  });
});

document.querySelectorAll("[data-story-type]").forEach((button) => {
  button.addEventListener("click", () => {
    state.storyType = button.dataset.storyType;
    document.querySelectorAll("[data-story-type]").forEach((candidate) => {
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

document.querySelectorAll("[data-generation-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    state.generationMode = button.dataset.generationMode;
    document.querySelectorAll("[data-generation-mode]").forEach((candidate) => {
      setSelected(candidate, candidate === button);
    });
  });
});

document.querySelectorAll("[data-primary-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    state.primaryMode = button.dataset.primaryMode;
    document.querySelectorAll("[data-primary-mode]").forEach((candidate) => {
      setSelected(candidate, candidate === button);
    });
  });
});

elements.idea.addEventListener("input", () => {
  elements.ideaCount.textContent = String(elements.idea.value.length);
});

elements.comicIdea.addEventListener("input", () => {
  elements.comicIdeaCount.textContent = String(elements.comicIdea.value.length);
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
  document.querySelectorAll("[data-generation-mode]").forEach((button) => {
    setSelected(button, button.dataset.generationMode === state.generationMode);
  });
};

const requestPayload = () => ({
  worlds: [...state.worlds],
  characters: [...state.characters],
  action: state.action,
  custom_idea: elements.idea.value.trim(),
  orientation: state.orientation,
  generation_mode: state.generationMode,
});

const comicPayload = () => ({
  worlds: [...state.worlds],
  characters: [...state.characters],
  story_type: state.storyType,
  custom_idea: elements.comicIdea.value.trim(),
  primary_mode: state.primaryMode,
});

async function createGeneration() {
  clearError();
  setLoading(true);
  try {
    const isComic = state.creationMode === "comic";
    const response = await fetch(isComic ? "/api/comics" : "/api/generations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(isComic ? comicPayload() : requestPayload()),
    });
    const data = await response.json();
    if (!response.ok) {
      const message = data.detail?.message || data.detail || "Generovanie sa nepodarilo spustiť.";
      throw new Error(message);
    }
    await pollGeneration(data.id, isComic);
  } catch (error) {
    setLoading(false);
    showBuilder();
    showError(error.message);
  }
}

async function pollGeneration(generationId, isComic = false) {
  clearTimeout(state.pollTimer);
  const response = await fetch(isComic ? `/api/comics/${generationId}` : `/api/generations/${generationId}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Stav generovania sa nepodarilo načítať.");
  if (data.status === "done") {
    setLoading(false);
    await showResult(data, isComic);
    return;
  }
  if (data.status === "failed") {
    throw new Error(data.error || "Generovanie zlyhalo.");
  }
  state.pollTimer = setTimeout(() => pollGeneration(generationId, isComic), 1200);
}

async function showResult(item, isComic = false) {
  state.current = item;
  elements.builderView.hidden = true;
  elements.resultView.hidden = false;
  elements.status.textContent = isComic ? "Komiksová knižka je hotová" : "Omaľovánka je hotová";
  elements.paperFrame.hidden = isComic;
  elements.comicPages.hidden = !isComic;
  elements.pngButton.hidden = isComic;
  elements.colorButton.hidden = isComic || !item.color_url;
  elements.patternPrintButton.hidden = isComic || !item.pattern_print_url;
  elements.comicColorPdfButton.hidden = !isComic;
  if (isComic) {
    renderComicPages(item);
    elements.printButton.href = item.line_art_pdf_url;
    elements.printButton.textContent = "Vytlačiť omaľovánkovú knižku";
    elements.pdfButton.href = item.line_art_pdf_url;
    elements.pdfButton.textContent = "Stiahnuť omaľovánkovú knižku";
    elements.comicColorPdfButton.href = item.color_pdf_url;
  } else {
    elements.recentSection.hidden = true;
    elements.resultImage.src = `${item.png_url}?v=${Date.now()}`;
    elements.paperFrame.className = `paper-frame ${item.request.orientation}`;
    elements.printButton.href = item.print_url;
    elements.printButton.textContent = "Vytlačiť bez vzoru";
    elements.patternPrintButton.href = item.pattern_print_url || item.print_url;
    elements.pngButton.href = item.png_url;
    elements.colorButton.href = item.color_url;
    elements.pdfButton.href = item.pdf_url;
    elements.pdfButton.textContent = "Stiahnuť PDF";
  }

  const labels = item.request.characters
    .map((id) => catalog.characters.find((character) => character.id === id)?.label)
    .filter(Boolean);
  const worldLabels = item.request.worlds
    .map((id) => catalog.worlds.find((world) => world.id === id)?.label)
    .filter(Boolean);
  const subjectText = labels.length ? labels.join(" + ") : worldLabels.join(" + ");
  if (isComic) {
    elements.resultSummary.textContent = `${subjectText} • 6 strán • A4 mini-zine`;
  } else {
    const orientation = item.request.orientation === "portrait" ? "na výšku" : "na šírku";
    elements.resultSummary.textContent = `${subjectText} • ${orientation} • pre deti 3–5 rokov`;
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (isComic) {
    elements.recentSection.hidden = true;
  } else {
    await loadRecent(item.id);
  }
}

function renderComicPages(item) {
  elements.comicPages.replaceChildren();
  const mode = item.request.primary_mode === "color" ? "color_url" : "line_art_url";
  item.pages.forEach((page) => {
    if (!page[mode]) return;
    const frame = document.createElement("div");
    frame.className = "comic-page-thumb";
    const image = document.createElement("img");
    image.src = `${page[mode]}?v=${Date.now()}`;
    image.alt = `Strana komiksu ${page.page_number}`;
    frame.append(image);
    elements.comicPages.append(frame);
  });
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
  elements.status.textContent = loading
    ? state.creationMode === "comic"
      ? "Kreslíme komiksovú knižku…"
      : "Kreslíme omaľovánku…"
    : "Pripravené na tvorenie";
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
syncCreationMode();
loadRecent();

function syncCreationMode() {
  const isComic = state.creationMode === "comic";
  elements.coloringOptions.hidden = isComic;
  elements.comicOptions.hidden = !isComic;
  elements.paperSetting.hidden = isComic;
  elements.renderSetting.hidden = isComic;
  elements.comicModeSetting.hidden = !isComic;
  elements.generateButton.lastChild.textContent = isComic
    ? " Vytvoriť komiksovú knižku"
    : " Vytvoriť omaľovánku";
  elements.generationEstimate.innerHTML = isComic
    ? "◷ 6 obrázkov <span>•</span> niekoľko minút"
    : "◷ 1 obrázok <span>•</span> približne minúta";
}
