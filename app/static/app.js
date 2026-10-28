const catalog = JSON.parse(document.querySelector("#catalogData").textContent);

let savedJobs = [];
try {
  savedJobs = JSON.parse(localStorage.getItem("omalovanky.jobs") || "[]");
  if (!Array.isArray(savedJobs)) savedJobs = [];
} catch {
  savedJobs = [];
}

const state = {
  characters: new Set(),
  scenes: new Set(),
  action: "playing",
  creationMode: "coloring",
  storyType: "trip",
  orientation: "landscape",
  generationMode: "line_art_direct",
  complexity: "simple",
  primaryMode: "line_art",
  current: null,
  pageCount: 1,
  genericCharacters: false,
  recentOffset: 0,
  jobs: savedJobs.filter((job) => Number.isInteger(job.id) && (job.kind === "comic" || job.kind === "generation")),
  pollTimers: new Map(),
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
  pdfButton: document.querySelector("#pdfButton"),
  jobsSection: document.querySelector("#jobsSection"),
  jobsRail: document.querySelector("#jobsRail"),
  renderModeControl: document.querySelector("#renderModeControl"),
  recentSection: document.querySelector("#recentSection"),
  recentRail: document.querySelector("#recentRail"),
};

const setSelected = (element, selected) => {
  element.classList.toggle("selected", selected);
  element.setAttribute("aria-pressed", String(selected));
};

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
    }
    elements.selectionHint.textContent = state.characters.size
      ? "Môžeš vybrať najviac 4 postavy."
      : "Postavy sú voliteľné. Vyber najviac 4.";
    elements.selectionHint.style.color = "";
    syncSelections();
  });
});

document.querySelectorAll("[data-scene-id]").forEach((button) => {
  button.addEventListener("click", () => {
    const sceneId = button.dataset.sceneId;
    if (state.scenes.has(sceneId)) state.scenes.delete(sceneId);
    else if (state.scenes.size < 4) state.scenes.add(sceneId);
    else document.querySelector("#sceneHint").textContent = "Vybrať sa dajú najviac 4 pozadia.";
    if (state.scenes.size < 4) document.querySelector("#sceneHint").textContent = "Vyber najviac 4 pozadia; spoja sa v jednej scéne.";
    syncSelections();
  });
});

document.querySelector("[data-no-background]").addEventListener("click", () => {
  state.scenes.clear();
  syncSelections();
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

document.querySelectorAll("[data-complexity]").forEach((button) => {
  button.addEventListener("click", () => {
    state.complexity = button.dataset.complexity;
    document.querySelectorAll("[data-complexity]").forEach((candidate) => setSelected(candidate, candidate === button));
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

document.querySelector("#editButton").addEventListener("click", restoreCurrent);
document.querySelector("#similarButton").addEventListener("click", restoreCurrent);
document.querySelector("#retryButton").addEventListener("click", () => { if (window.confirm("Vygenerovať nový obrázok? Vznikne nová platená úloha.")) { restoreCurrent(); createGeneration(); } });
document.querySelector("#helpButton").addEventListener("click", () => document.querySelector("#helpDialog").showModal());
document.querySelector("#settingsButton").addEventListener("click", () => {
  elements.resultView.hidden = true;
  elements.builderView.hidden = false;
  const settings = document.querySelector("#generationSettings");
  settings.scrollIntoView({ behavior: "smooth", block: "center" });
  settings.focus({ preventScroll: true });
});

const syncSelections = () => {
  document.querySelectorAll(".character-card").forEach((button) => {
    setSelected(button, state.characters.has(button.dataset.characterId));
  });
  document.querySelectorAll(".scene-card").forEach((button) => {
    setSelected(button, state.scenes.has(button.dataset.sceneId));
  });
  setSelected(document.querySelector("[data-no-background]"), state.scenes.size === 0);
  document.querySelectorAll("[data-generation-mode]").forEach((button) => {
    setSelected(button, button.dataset.generationMode === state.generationMode);
  });
};

const selectedWorlds = () => [...new Set([...state.characters]
  .map((id) => catalog.characters.find((character) => character.id === id)?.world_id)
  .filter(Boolean))];

const requestPayload = () => ({
  page_count: state.pageCount,
  complexity: state.complexity,
  generic_characters: state.genericCharacters,
  worlds: selectedWorlds(),
  characters: [...state.characters],
  scenes: [...state.scenes],
  action: state.action,
  custom_idea: elements.idea.value.trim(),
  orientation: state.orientation,
  generation_mode: state.generationMode,
});

document.querySelector("#pageCount").addEventListener("input", (event) => {
  state.pageCount = Number(event.target.value);
  syncCreationMode();
});

document.querySelector("#jobIndicator").addEventListener("click", () => {
  elements.resultView.hidden = true;
  elements.builderView.hidden = false;
  elements.jobsSection.scrollIntoView({ behavior: "smooth", block: "start" });
});

const comicPayload = () => ({
  generic_characters: state.genericCharacters,
  worlds: selectedWorlds(),
  characters: [...state.characters],
  scenes: [...state.scenes],
  story_type: state.storyType,
  custom_idea: elements.comicIdea.value.trim(),
  primary_mode: state.primaryMode,
});

document.querySelector("#previewPromptButton").addEventListener("click", async () => {
  const preview = document.querySelector("#promptPreview");
  preview.textContent = "Načítavam zadanie…";
  try {
    const isComic = state.creationMode === "comic";
    const response = await fetch(isComic ? "/api/comics/prompt" : "/api/generations/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(isComic ? comicPayload() : requestPayload()),
    });
    if (!response.ok) throw new Error("Zadanie sa nepodarilo načítať.");
    preview.textContent = (await response.json()).prompts.join("\n\n──────────\n\n");
  } catch (error) {
    preview.textContent = error.message;
  }
});

elements.form.addEventListener("input", () => {
  document.querySelector("#promptPreview").textContent = "";
});
elements.form.addEventListener("click", (event) => {
  if (!event.target.closest(".prompt-preview")) document.querySelector("#promptPreview").textContent = "";
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
    trackJob({ id: data.id, kind: isComic ? "comic" : "generation" });
    setLoading(false);
    showBuilder();
    elements.status.textContent = "Úloha pridaná do fronty";
  } catch (error) {
    handleGenerationError(error);
  }
}

function trackJob(job) {
  if (!state.jobs.some((item) => item.id === job.id && item.kind === job.kind)) state.jobs.unshift(job);
  state.jobs = state.jobs.slice(0, 20);
  persistJobs();
  renderJobs();
  pollJob(job);
}

function persistJobs() {
  localStorage.setItem("omalovanky.jobs", JSON.stringify(state.jobs.map(({ id, kind }) => ({ id, kind }))));
}

async function pollJob(job) {
  const url = job.kind === "comic" ? `/api/comics/${job.id}` : `/api/generations/${job.id}`;
  let data;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Stav generovania sa nepodarilo načítať.");
    data = await response.json();
  } catch {
    job.connectionError = true;
    renderJobs();
    state.pollTimers.set(`${job.kind}:${job.id}`, setTimeout(() => pollJob(job), 5000));
    return;
  }
  job.connectionError = false;
  if (data.status === "done") {
    job.data = data;
    job.status = "done";
    renderJobs();
    return;
  }
  if (data.status === "failed") {
    job.data = data;
    failJob(job, new Error(data.error || "Generovanie zlyhalo."));
    return;
  }
  job.data = data;
  job.status = data.status;
  renderJobs();
  state.pollTimers.set(`${job.kind}:${job.id}`, setTimeout(() => {
    pollJob(job);
  }, 1200));
}

function failJob(job, error) {
  clearTimeout(state.pollTimers.get(`${job.kind}:${job.id}`));
  job.status = "failed";
  job.error = error instanceof Error ? error.message : String(error);
  renderJobs();
  showError(job.error);
}

function handleGenerationError(error) {
  setLoading(false);
  showBuilder();
  showError(error instanceof Error ? error.message : String(error));
}

function renderJobs() {
  elements.jobsRail.replaceChildren();
  elements.jobsSection.hidden = state.jobs.length === 0;
  const active = state.jobs.filter((job) => job.status !== "done" && job.status !== "failed").length;
  const done = state.jobs.filter((job) => job.status === "done").length;
  const indicator = document.querySelector("#jobIndicator");
  indicator.hidden = state.jobs.length === 0;
  indicator.textContent = active ? `Úlohy: ${active} prebieha` : `Úlohy: ${done} hotových`;
  state.jobs.forEach((job) => {
    const card = document.createElement("article");
    card.className = "job-card";
    const data = job.data || {};
    const total = data.total_pages || data.total_steps || 1;
    const completed = data.completed_pages ?? data.completed_steps ?? 0;
    const phase = job.connectionError ? "Čaká na spojenie" : job.status === "done" ? "Hotovo" : job.status === "failed" ? "Nepodarilo sa" :
      data.phase === "processing" ? "Spracúvame výstup" : data.status === "running" ? "Generujeme" : "Čaká vo fronte";
    card.innerHTML = `<strong>${job.kind === "comic" ? "Komiksová knižka" : "Omaľovánka"} #${job.id}</strong><span>${phase}</span><small>${completed}/${total}</small>`;
    if (job.status === "done") {
      const open = document.createElement("button");
      open.type = "button";
      open.textContent = "Otvoriť";
      open.addEventListener("click", () => openJob(job));
      card.append(open);
    } else if (job.status === "failed") {
      const error = document.createElement("small");
      error.className = "job-error";
      error.textContent = job.error;
      card.append(error);
      if (data.request && !data.request.generic_characters) {
        const note = document.createElement("small");
        note.className = "job-retry-note";
        note.textContent = "Názvy postáv vo vlastnom nápade sa nezmenia.";
        card.append(note);
        const retry = document.createElement("button");
        retry.type = "button";
        retry.textContent = "Skúsiť so všeobecnými postavami";
        retry.addEventListener("click", async () => {
          retry.disabled = true;
          try {
            const response = await fetch(job.kind === "comic" ? "/api/comics" : "/api/generations", {
              method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ ...data.request, generic_characters: true }),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail?.message || result.detail || "Úlohu sa nepodarilo spustiť.");
            trackJob({ id: result.id, kind: job.kind });
          } catch (error) {
            showError(error.message);
          } finally {
            retry.disabled = false;
          }
        });
        card.append(retry);
      }
    }
    elements.jobsRail.append(card);
  });
}

async function openJob(job) {
  try {
    const response = await fetch(job.kind === "comic" ? `/api/comics/${job.id}` : `/api/generations/${job.id}`);
    if (!response.ok) throw new Error("Výsledok sa nepodarilo načítať.");
    await showResult(await response.json(), job.kind === "comic");
  } catch (error) {
    showError(error.message);
  }
}

async function showResult(item, isComic = false) {
  state.current = item;
  state.currentIsComic = isComic;
  elements.builderView.hidden = true;
  elements.resultView.hidden = false;
  elements.status.textContent = isComic ? "Komiksová knižka je hotová" : "Omaľovánka je hotová";
  const multiPage = !isComic && item.request.page_count > 1;
  elements.paperFrame.hidden = isComic || multiPage;
  elements.comicPages.hidden = !isComic && !multiPage;
  document.querySelector("#resultTitle").textContent = isComic ? "Knižka je hotová!" : item.request.generation_mode === "color_first" ? "Farebný obrázok je hotový!" : "Hotovo! Môžeme vyfarbovať.";
  document.querySelector("#comicInstructions").hidden = !isComic;
  const alternate = document.querySelector("#alternatePdfButton");
  alternate.hidden = true;
  if (isComic) {
    renderComicPages(item);
    elements.pdfButton.href = item.request.primary_mode === "color" ? item.color_pdf_url : item.line_art_pdf_url;
    elements.pdfButton.textContent = "Stiahnuť PDF knižky";
    alternate.href = item.request.primary_mode === "color" ? item.line_art_pdf_url : item.color_pdf_url;
    alternate.textContent = item.request.primary_mode === "color" ? "Stiahnuť omaľovánkovú knižku" : "Stiahnuť farebnú knižku";
    alternate.hidden = !item.color_pdf_url || !item.line_art_pdf_url;
  } else {
    if (multiPage) renderComicPages({ ...item, request: { primary_mode: item.request.generation_mode === "color_first" ? "color" : "line_art" } });
    const previewUrl = item.request.generation_mode === "color_first" ? (item.color_url || item.png_url) : item.png_url;
    elements.resultImage.onerror = () => {
      elements.resultImage.onerror = null;
      if (previewUrl !== item.png_url && item.png_url) elements.resultImage.src = `${item.png_url}?v=${Date.now()}`;
    };
    elements.resultImage.src = `${previewUrl}?v=${Date.now()}`;
    elements.paperFrame.className = `paper-frame ${item.request.orientation}`;
    elements.pdfButton.href = item.request.generation_mode === "color_first" ? (item.color_pdf_url || item.pdf_url) : item.pdf_url;
    elements.pdfButton.textContent = item.request.generation_mode === "color_first" ? "Stiahnuť farebné PDF" : "Stiahnuť PDF";
    if (item.request.generation_mode === "color_first" && item.pdf_url) {
      alternate.href = item.pdf_url;
      alternate.textContent = "Stiahnuť omaľovánkové PDF";
      alternate.hidden = false;
    }
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
    const complexity = { simple: "jednoduchá", medium: "stredná", detailed: "detailná" }[item.request.complexity || "simple"];
    elements.resultSummary.textContent = `${subjectText} • ${orientation} • ${complexity}`;
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
  await loadRecent(item.id);
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
  elements.resultView.hidden = true;
  elements.builderView.hidden = false;
  elements.status.textContent = "Pripravené na tvorenie";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function restoreCurrent() {
  const request = state.current.request;
  state.genericCharacters = request.generic_characters || false;
  state.creationMode = state.currentIsComic ? "comic" : "coloring";
  state.characters = new Set(request.characters);
  state.scenes = new Set(request.scenes);
  state.action = request.action || "playing";
  state.storyType = request.story_type || "trip";
  state.orientation = request.orientation || "landscape";
  state.generationMode = request.generation_mode || "line_art_direct";
  state.complexity = request.complexity || "simple";
  state.pageCount = request.page_count || 1;
  document.querySelector("#pageCount").value = state.pageCount;
  state.primaryMode = request.primary_mode || "line_art";
  elements.idea.value = state.currentIsComic ? "" : request.custom_idea;
  elements.comicIdea.value = state.currentIsComic ? request.custom_idea : "";
  elements.ideaCount.textContent = elements.idea.value.length;
  elements.comicIdeaCount.textContent = elements.comicIdea.value.length;
  for (const [selector, key, value] of [["[data-creation-mode]", "creationMode", state.creationMode], ["[data-action-id]", "actionId", state.action], ["[data-story-type]", "storyType", state.storyType], ["[data-orientation]", "orientation", state.orientation], ["[data-primary-mode]", "primaryMode", state.primaryMode], ["[data-complexity]", "complexity", state.complexity]]) {
    document.querySelectorAll(selector).forEach((button) => setSelected(button, button.dataset[key] === value));
  }
  syncSelections();
  syncCreationMode();
  showBuilder();
}

async function loadRecent(selectedId = null, append = false) {
  try {
    if (!append) state.recentOffset = 0;
    const responses = await Promise.all([fetch(`/api/colorings?limit=20&offset=${state.recentOffset}`), fetch(`/api/comics?limit=20&offset=${state.recentOffset}`)]);
    if (responses.some((response) => !response.ok)) return;
    const [colorings, comics] = await Promise.all(responses.map((response) => response.json()));
    if (!append) elements.recentRail.replaceChildren();
    [...colorings.map((item) => ({ item, isComic: false })), ...comics.map((item) => ({ item, isComic: true }))].sort((a, b) => (b.item.completed_at || "").localeCompare(a.item.completed_at || "")).forEach(({ item, isComic }) => {
      const button = document.createElement("button");
      button.className = `recent-item ${item.id === selectedId ? "selected" : ""}`;
      button.type = "button";
      const subject = item.request.characters.map((id) => catalog.characters.find((c) => c.id === id)?.label).filter(Boolean).join(", ");
      button.setAttribute("aria-label", `Otvoriť ${isComic ? "komiks" : "omaľovánku"} ${item.id}${subject ? ": " + subject : ""}`);
      const image = document.createElement("img");
      image.src = isComic ? item.pages[0]?.color_url : (item.color_url || item.png_url);
      image.alt = "";
      button.append(image);
      const label = document.createElement("span");
      const date = item.completed_at ? new Date(item.completed_at).toLocaleDateString("sk-SK") : "";
      label.textContent = `${isComic ? "Komiks" : "Omaľovánka"}${date ? " · " + date : ""}${subject ? " · " + subject : ""}`;
      button.append(label);
      button.addEventListener("click", () => showResult(item, isComic));
      elements.recentRail.append(button);
    });
    elements.recentSection.hidden = elements.recentRail.children.length === 0;
    document.querySelector("#loadMoreRecent").hidden = colorings.length < 20 && comics.length < 20;
    state.recentOffset += 20;
  } catch {
    elements.recentSection.hidden = true;
  }
}
document.querySelector("#loadMoreRecent").addEventListener("click", () => loadRecent(null, true));

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
state.jobs.forEach((job) => pollJob(job));
renderJobs();

function syncCreationMode() {
  const isComic = state.creationMode === "comic";
  elements.coloringOptions.hidden = isComic;
  elements.comicOptions.hidden = !isComic;
  elements.paperSetting.hidden = isComic;
  elements.renderSetting.hidden = isComic;
  elements.comicModeSetting.hidden = !isComic;
  document.querySelector("#pageCountSetting").hidden = isComic;
  elements.generateButton.lastChild.textContent = isComic
    ? " Vytvoriť komiksovú knižku"
    : " Vytvoriť omaľovánku";
  elements.generationEstimate.innerHTML = isComic
    ? "◷ 6 obrázkov <span>•</span> niekoľko minút"
    : `◷ ${state.pageCount || 1} obrázkov <span>•</span> približne ${state.pageCount || 1} minút`;
}
