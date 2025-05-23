function regionBoxChange(event) {
  let name = event.target.id.slice(4).toLowerCase(); // Strip the "show" prefix
  document.controls.regions.find((r) => r.name === name).show =
    event.target.checked;
  applySettings();
}

function alignmentChange(event) {
  let x = event.target.x.baseVal.value;
  let y = event.target.y.baseVal.value;
  document.controls.alignHorizontal = x === 0 ? -1 : x === 75 ? 1 : 0;
  document.controls.alignVertical = y === 0 ? -1 : y === 75 ? 1 : 0;
  applySettings();
}

function addControls(svgElem) {
  document.controls = {
    regions: [],
    alignHorizontal: 0,
    alignVertical: 0,
    svgElem: svgElem,
  };

  for (const child of svgElem.children) {
    if (child.id.endsWith("Region") && child.dataset.extents) {
      let nums = child.dataset.extents.split(" ");
      let region = {
        name: child.id.slice(0, -6), // Remove "Region" suffix
        top: parseFloat(nums[0]),
        right: parseFloat(nums[1]),
        bottom: parseFloat(nums[2]),
        left: parseFloat(nums[3]),
        show: true,
      };
      document.controls.regions.push(region);
    }
  }

  let container = document.createElement("div");
  container.classList.add("controls");
  document.body.appendChild(container);

  let checks = document.createElement("p");
  container.appendChild(checks);
  let checksPrompt = document.createElement("span");
  checksPrompt.innerText = "Show regions:";
  checks.appendChild(checksPrompt);

  for (const region of document.controls.regions) {
    let capitalised = region.name[0].toUpperCase() + region.name.slice(1);

    let span = document.createElement("span");
    checks.appendChild(span);

    let checkbox = document.createElement("input");
    checkbox.id = "show" + capitalised;
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.addEventListener("change", regionBoxChange);
    span.appendChild(checkbox);

    let label = document.createElement("label");
    label.innerText = region.name;
    label.setAttribute("for", "show" + capitalised);
    span.appendChild(label);
  }

  let alignment = document.createElement("p");
  container.appendChild(alignment);
  alignment.innerHTML = `
    <span>Screen alignment:</span>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="4em" height="4em">
      <g id="alignGroup" stroke="none" fill="currentColor">
        <rect x="0" y="0" width="25" height="25" rx="5" />
        <rect x="37.5" y="0" width="25" height="25" rx="5" />
        <rect x="75" y="0" width="25" height="25" rx="5" />
        <rect x="0" y="37.5" width="25" height="25" rx="5" />
        <rect x="37.5" y="37.5" width="25" height="25" rx="5" />
        <rect x="75" y="37.5" width="25" height="25" rx="5" />
        <rect x="0" y="75" width="25" height="25" rx="5" />
        <rect x="37.5" y="75" width="25" height="25" rx="5" />
        <rect x="75" y="75" width="25" height="25" rx="5" />
      </g>
    </svg>`;

  for (rect of document.getElementById("alignGroup").children) {
    rect.addEventListener("click", alignmentChange);
  }

  window.addEventListener("load", () => parseLocation());
}

function applySettings() {
  const controls = document.controls;
  const regions = document.controls.regions;

  for (const region of regions) {
    document.getElementById(region.name + "Region").style.display = region.show
      ? "block"
      : "none";
    let capitalised = region.name[0].toUpperCase() + region.name.slice(1);
    document.getElementById("show" + capitalised).checked = region.show;
  }

  let top = Math.min(...regions.filter((r) => r.show).map((r) => r.top));
  top = isFinite(top) ? top : 0;
  let right = Math.max(...regions.filter((r) => r.show).map((r) => r.right));
  right = isFinite(right) ? right : 0;
  let bottom = Math.max(...regions.filter((r) => r.show).map((r) => r.bottom));
  bottom = isFinite(bottom) ? bottom : 0;
  let left = Math.min(...regions.filter((r) => r.show).map((r) => r.left));
  left = isFinite(left) ? left : 0;
  controls.svgElem.setAttribute(
    "viewBox",
    `${left} ${top} ${right - left} ${bottom - top}`
  );

  let alignment =
    (controls.alignHorizontal === -1
      ? "xMin"
      : controls.alignHorizontal === 1
      ? "xMax"
      : "xMid") +
    (controls.alignVertical === -1
      ? "YMin"
      : controls.alignVertical === 1
      ? "YMax"
      : "YMid");
  controls.svgElem.setAttribute("preserveAspectRatio", alignment + " meet");

  let selectedX =
    document.controls.alignHorizontal === -1
      ? 0
      : document.controls.alignHorizontal === 0
      ? 37.5
      : 75;
  let selectedY =
    document.controls.alignVertical === -1
      ? 0
      : document.controls.alignVertical === 0
      ? 37.5
      : 75;

  for (rect of document.getElementById("alignGroup").children) {
    let x = rect.x.baseVal.value;
    let y = rect.y.baseVal.value;
    rect.style.fill = x === selectedX && y === selectedY ? "#0f0" : "inherit";
  }

  let hashParts = [];
  if (!document.controls.regions.every((r) => r.show)) {
    // When everything is shown, don't put that into location
    let shown = [];
    for (const region of document.controls.regions) {
      if (region.show) shown.push(region.name);
    }
    if (shown.length === 0) shown.push("none");
    hashParts.push(shown.join(","));
  }
  if (alignment !== "xMidYMid") hashParts.push(alignment);

  if (hashParts.length === 0)
    history.pushState("", document.title, window.location.pathname);
  else document.location.hash = hashParts.join("|");
}

function parseLocation() {
  let hash = document.location.hash.replace("#", "");

  const alignRe = /^xM(\w\w)YM(\w\w)$/;
  const regionRe = new RegExp(
    "(" + document.controls.regions.map((r) => r.name).join("|") + "|none)",
    "i"
  );
  for (part of hash.split("|")) {
    if (alignRe.test(part)) {
      let m = part.match(alignRe);
      settings.alignHorizontal = m[1] === "in" ? -1 : m[1] === "ax" ? 1 : 0;
      settings.alignVertical = m[2] === "in" ? -1 : m[2] === "ax" ? 1 : 0;
    }
    if (regionRe.test(part)) {
      for (let i = 0; i < document.controls.regions.length; i++) {
        const region = document.controls.regions[i];
        if (part.includes(region.name))
          document.controls.regions[i].show = true;
        else document.controls.regions[i].show = false;
      }
    }
  }

  applySettings();
}

function showRegions() {
  for (const region of document.controls.regions) {
    let rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", region.left);
    rect.setAttribute("y", region.top);
    rect.setAttribute("width", region.right - region.left);
    rect.setAttribute("height", region.bottom - region.top);
    rect.setAttribute("fill", "#f0f");
    rect.setAttribute("fill-opacity", 0.5);
    document.controls.svgElem.appendChild(rect);
  }
}
