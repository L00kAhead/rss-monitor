const API_BASE_URL = window.location.origin; // Dynamically get base URL

let selectedFilterKeywords = []; // Array to hold currently selected filter keywords
let allAvailableKeywords = []; // To store all keywords for the datalist

document.addEventListener("DOMContentLoaded", () => {
  // Initial loads
  loadKeywords();
  loadRSSFeeds();
  loadResults(1); // Load first page of results

  // Setup auto-refresh for results
  setupAutoRefresh();

  // Event Listeners for Forms
  document
    .getElementById("keywordForm")
    .addEventListener("submit", handleAddKeyword);
  document
    .getElementById("rssFeedForm")
    .addEventListener("submit", handleAddRSSFeed);

  // New filter UI event listeners
  document
    .getElementById("addFilterTagBtn")
    .addEventListener("click", addFilterTagFromInput);
  document
    .getElementById("filterKeywordInput")
    .addEventListener("keypress", (event) => {
      if (event.key === "Enter") {
        event.preventDefault(); // Prevent form submission
        addFilterTagFromInput();
      }
    });
  document
    .getElementById("clearAllFiltersBtn")
    .addEventListener("click", clearAllFilters);

  //  Modal for editing 
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.innerHTML = `
        <div class="modal-content">
            <span class="close-button">&times;</span>
            <h3 id="modalTitle">Edit Item</h3>
            <form id="editForm">
                </form>
        </div>
    `;
  document.body.appendChild(modal);

  modal.querySelector(".close-button").addEventListener("click", () => {
    modal.style.display = "none";
  });
  window.addEventListener("click", (event) => {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });

  // Handle global errors
  window.onerror = function (message, source, lineno, colno, error) {
    console.error(
      "Global Error Caught:",
      message,
      source,
      lineno,
      colno,
      error
    );
    // alert("An error occurred: " + message); // For debugging, remove in production
  };
});

async function fetchApi(endpoint, method = "GET", data = null) {
  const options = {
    method: method,
    headers: {
      "Content-Type": "application/json",
    },
  };
  if (data) {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail ||
          `API error: ${response.status} ${response.statusText}`
      );
    }
    if (response.status === 204) {
      // No Content
      return null;
    }
    return await response.json();
  } catch (error) {
    console.error("Fetch API error:", error);
    alert(`Error: ${error.message}`);
    throw error; // Re-throw to allow specific error handling
  }
}

//  Keyword Functions 
async function loadKeywords() {
  try {
    const keywords = await fetchApi("/keywords/");
    const keywordsListDiv = document.getElementById("keywordsList");
    keywordsListDiv.innerHTML = ""; // Clear previous list
    allAvailableKeywords = keywords.map((kw) => kw.keyword); // Store for datalist

    if (keywords.length === 0) {
      keywordsListDiv.innerHTML =
        '<p class="empty-list-message">No keywords added yet.</p>';
      populateDatalist([]);
      return;
    }

    keywords.forEach((kw) => {
      const item = document.createElement("div");
      item.className = "list-item";
      item.innerHTML = `
                <span>${kw.keyword}</span>
                <div class="actions">
                    <button class="btn toggle-btn btn-warning" data-id="${
                      kw.id
                    }" data-active="${kw.is_active}" title="${
        kw.is_active
          ? "Pause monitoring for this keyword"
          : "Resume monitoring for this keyword"
      }">
                        <i class="fas ${
                          kw.is_active ? "fa-pause" : "fa-play"
                        }"></i>
                    </button>
                    <button class="btn edit-btn btn-secondary" data-id="${
                      kw.id
                    }" data-keyword="${kw.keyword}" data-active="${
        kw.is_active
      }" title="Edit keyword">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn delete-btn btn-danger" data-id="${
                      kw.id
                    }" title="Delete keyword">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;
      keywordsListDiv.appendChild(item);
    });

    keywordsListDiv.querySelectorAll(".toggle-btn").forEach((button) => {
      button.addEventListener("click", handleToggleKeyword);
    });
    keywordsListDiv.querySelectorAll(".edit-btn").forEach((button) => {
      button.addEventListener("click", handleEditKeyword);
    });
    keywordsListDiv.querySelectorAll(".delete-btn").forEach((button) => {
      button.addEventListener("click", handleDeleteKeyword);
    });

    populateDatalist(allAvailableKeywords);
  } catch (error) {
    console.error("Failed to load keywords:", error);
    document.getElementById("keywordsList").innerHTML =
      '<p class="error-message">Error loading keywords.</p>';
  }
}

async function handleAddKeyword(event) {
  event.preventDefault();
  const keywordInput = document.getElementById("keywordInput");
  const keyword = keywordInput.value.trim();

  if (keyword) {
    try {
      await fetchApi("/keywords/", "POST", { keyword: keyword });
      keywordInput.value = ""; // Clear input
      await loadKeywords(); // Refresh list and datalist
      loadResults(1); // Refresh results to show new matches
    } catch (error) {
      // Error handled by fetchApi
    }
  }
}

async function handleToggleKeyword(event) {
  const button = event.target.closest("button"); // Use closest to get the button even if icon is clicked
  const id = button.dataset.id;
  const isActive = button.dataset.active === "true";
  try {
    await fetchApi(`/keywords/${id}`, "PUT", { is_active: !isActive });
    await loadKeywords();
    loadResults(1); // Refresh results
  } catch (error) {
    // Error handled by fetchApi
  }
}

function handleEditKeyword(event) {
  const button = event.target.closest("button");
  const id = button.dataset.id;
  const currentKeyword = button.dataset.keyword;
  const currentActive = button.dataset.active === "true";

  const modal = document.querySelector(".modal");
  const modalTitle = document.getElementById("modalTitle");
  const editForm = document.getElementById("editForm");

  modalTitle.textContent = `Edit Keyword: ${currentKeyword}`;
  editForm.innerHTML = `
        <label for="editKeywordText">Keyword:</label>
        <input type="text" id="editKeywordText" value="${currentKeyword}" required>
        <label>
            <input type="checkbox" id="editKeywordActive" ${
              currentActive ? "checked" : ""
            }> Is Active
        </label>
        <button type="submit" class="btn btn-secondary">Save Changes</button>
    `;
  modal.style.display = "flex"; // Use flex to center

  editForm.onsubmit = async (e) => {
    e.preventDefault();
    const updatedKeyword = document
      .getElementById("editKeywordText")
      .value.trim();
    const updatedActive = document.getElementById("editKeywordActive").checked;
    if (updatedKeyword) {
      try {
        await fetchApi(`/keywords/${id}`, "PUT", {
          keyword: updatedKeyword,
          is_active: updatedActive,
        });
        modal.style.display = "none";
        await loadKeywords();
        loadResults(1); // Refresh results
      } catch (error) {
        // Error handled by fetchApi
      }
    }
  };
}

async function handleDeleteKeyword(event) {
  const id = event.target.closest("button").dataset.id;
  if (confirm("Are you sure you want to delete this keyword?")) {
    try {
      await fetchApi(`/keywords/${id}`, "DELETE");
      await loadKeywords();
      loadResults(1); // Refresh results
    } catch (error) {
      // Error handled by fetchApi
    }
  }
}

//  RSS Feed Functions 
async function loadRSSFeeds() {
  try {
    const feeds = await fetchApi("/rss-feeds/");
    const rssFeedsListDiv = document.getElementById("rssFeedsList");
    rssFeedsListDiv.innerHTML = ""; // Clear previous list

    if (feeds.length === 0) {
      rssFeedsListDiv.innerHTML =
        '<p class="empty-list-message">No RSS feeds added yet.</p>';
      return;
    }

    feeds.forEach((feed) => {
      const item = document.createElement("div");
      item.className = "list-item";
      const lastFetched = feed.last_fetched
        ? new Date(feed.last_fetched).toLocaleString()
        : "Never";
      item.innerHTML = `
                <span>
                    <strong>${feed.name || feed.url}</strong><br>
                    <small>${feed.url}</small><br>
                    <small>Interval: ${
                      feed.fetch_interval_minutes
                    } min | Last Fetched: ${lastFetched}</small>
                </span>
                <div class="actions">
                    <button class="btn toggle-btn btn-warning" data-id="${
                      feed.id
                    }" data-active="${feed.is_active}" title="${
        feed.is_active
          ? "Pause monitoring for this feed"
          : "Resume monitoring for this feed"
      }">
                        <i class="fas ${
                          feed.is_active ? "fa-pause" : "fa-play"
                        }"></i>
                    </button>
                    <button class="btn edit-btn btn-secondary" data-id="${
                      feed.id
                    }" data-url="${feed.url}" data-name="${
        feed.name || ""
      }" data-interval="${feed.fetch_interval_minutes}" data-active="${
        feed.is_active
      }" title="Edit feed settings">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn refetch-btn btn-refetch" data-id="${
                      feed.id
                    }" title="Manually re-fetch this feed">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    <button class="btn delete-btn btn-danger" data-id="${
                      feed.id
                    }" title="Delete feed and its results">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;
      rssFeedsListDiv.appendChild(item);
    });

    rssFeedsListDiv.querySelectorAll(".toggle-btn").forEach((button) => {
      button.addEventListener("click", handleToggleRSSFeed);
    });
    rssFeedsListDiv.querySelectorAll(".edit-btn").forEach((button) => {
      button.addEventListener("click", handleEditRSSFeed);
    });
    rssFeedsListDiv.querySelectorAll(".refetch-btn").forEach((button) => {
      button.addEventListener("click", handleRefetchRSSFeed);
    });
    rssFeedsListDiv.querySelectorAll(".delete-btn").forEach((button) => {
      button.addEventListener("click", handleDeleteRSSFeed);
    });
  } catch (error) {
    console.error("Failed to load RSS Feeds:", error);
    document.getElementById("rssFeedsList").innerHTML =
      '<p class="error-message">Error loading RSS feeds.</p>';
  }
}

async function handleAddRSSFeed(event) {
  event.preventDefault();
  const rssUrlInput = document.getElementById("rssUrlInput");
  const rssNameInput = document.getElementById("rssNameInput");
  const rssIntervalInput = document.getElementById("rssIntervalInput");

  const url = rssUrlInput.value.trim();
  const name = rssNameInput.value.trim() || null;
  const interval = parseInt(rssIntervalInput.value, 10);

  if (url) {
    try {
      await fetchApi("/rss-feeds/", "POST", {
        url: url,
        name: name,
        fetch_interval_minutes: interval,
      });
      rssUrlInput.value = "";
      rssNameInput.value = "";
      rssIntervalInput.value = "5"; // Reset to default
      await loadRSSFeeds();
    } catch (error) {
      // Error handled by fetchApi
    }
  }
}

async function handleToggleRSSFeed(event) {
  const button = event.target.closest("button");
  const id = button.dataset.id;
  const isActive = button.dataset.active === "true";
  try {
    await fetchApi(`/rss-feeds/${id}`, "PUT", { is_active: !isActive });
    await loadRSSFeeds();
  } catch (error) {
    // Error handled by fetchApi
  }
}

function handleEditRSSFeed(event) {
  const button = event.target.closest("button");
  const id = button.dataset.id;
  const currentUrl = button.dataset.url;
  const currentName = button.dataset.name;
  const currentInterval = button.dataset.interval;
  const currentActive = button.dataset.active === "true";

  const modal = document.querySelector(".modal");
  const modalTitle = document.getElementById("modalTitle");
  const editForm = document.getElementById("editForm");

  modalTitle.textContent = `Edit RSS Feed: ${currentName || currentUrl}`;
  editForm.innerHTML = `
        <label for="editRssUrl">URL:</label>
        <input type="url" id="editRssUrl" value="${currentUrl}" required>
        <label for="editRssName">Name:</label>
        <input type="text" id="editRssName" value="${currentName}">
        <label for="editRssInterval">Fetch Interval (minutes):</label>
        <input type="number" id="editRssInterval" min="1" value="${currentInterval}" required>
        <label>
            <input type="checkbox" id="editRssActive" ${
              currentActive ? "checked" : ""
            }> Is Active
        </label>
        <button type="submit" class="btn btn-secondary">Save Changes</button>
    `;
  modal.style.display = "flex";

  editForm.onsubmit = async (e) => {
    e.preventDefault();
    const updatedUrl = document.getElementById("editRssUrl").value.trim();
    const updatedName =
      document.getElementById("editRssName").value.trim() || null;
    const updatedInterval = parseInt(
      document.getElementById("editRssInterval").value,
      10
    );
    const updatedActive = document.getElementById("editRssActive").checked;

    if (updatedUrl && updatedInterval) {
      try {
        await fetchApi(`/rss-feeds/${id}`, "PUT", {
          url: updatedUrl,
          name: updatedName,
          fetch_interval_minutes: updatedInterval,
          is_active: updatedActive,
        });
        modal.style.display = "none";
        await loadRSSFeeds();
      } catch (error) {
        // Error handled by fetchApi
      }
    }
  };
}

async function handleRefetchRSSFeed(event) {
  const id = event.target.closest("button").dataset.id;
  if (
    confirm(
      "Are you sure you want to trigger a manual re-fetch for this feed? This may take a moment."
    )
  ) {
    try {
      await fetchApi(`/rss-feeds/${id}/refetch`, "POST");
      alert(
        "Re-fetch initiated. Results will be updated shortly if new matches are found."
      );
      await loadRSSFeeds(); // Refresh status to show last fetched time updated
    } catch (error) {
      // Error handled by fetchApi
    }
  }
}

async function handleDeleteRSSFeed(event) {
  const id = event.target.closest("button").dataset.id;
  if (
    confirm(
      "Are you sure you want to delete this RSS feed and all its associated results?"
    )
  ) {
    try {
      await fetchApi(`/rss-feeds/${id}`, "DELETE");
      await loadRSSFeeds();
      loadResults(1); // Refresh results as some might be deleted
    } catch (error) {
      // Error handled by fetchApi
    }
  }
}

//  Results Functions 
let currentPage = 1;
const AUTO_REFRESH_INTERVAL_MS = 60000; // Refresh every 60 seconds (1 minute)
let autoRefreshTimer;

function setupAutoRefresh() {
  // Clear any existing timer to prevent multiple intervals
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
  }
  autoRefreshTimer = setInterval(() => {
    console.log("Auto-refreshing results...");
    loadResults(currentPage, true); // Pass a flag to indicate it's an auto-refresh
  }, AUTO_REFRESH_INTERVAL_MS);
}

// Populates the datalist for the filter input
function populateDatalist(keywords) {
  const datalist = document.getElementById("availableKeywords");
  datalist.innerHTML = ""; // Clear previous options
  keywords.forEach((kw) => {
    const option = document.createElement("option");
    option.value = kw;
    datalist.appendChild(option);
  });
}

// Renders the active filter tags
function renderActiveFilterTags() {
  const activeFilterTagsContainer = document.getElementById("activeFilterTags");
  activeFilterTagsContainer.innerHTML = ""; // Clear previous tags

  if (selectedFilterKeywords.length === 0) {
    activeFilterTagsContainer.innerHTML =
      '<span class="empty-tags-message">No filters applied.</span>';
    return;
  }

  selectedFilterKeywords.forEach((keyword) => {
    const tag = document.createElement("div");
    tag.className = "filter-tag";
    tag.innerHTML = `
            <span class="tag-text">${keyword}</span>
            <button class="remove-tag-btn" data-keyword="${keyword}">&times;</button>
        `;
    tag.querySelector(".remove-tag-btn").addEventListener("click", (event) => {
      removeFilterTag(event.target.dataset.keyword);
    });
    activeFilterTagsContainer.appendChild(tag);
  });
}

// Adds a filter tag from the input field
function addFilterTagFromInput() {
  const filterInput = document.getElementById("filterKeywordInput");
  const keyword = filterInput.value.trim();

  if (keyword && !selectedFilterKeywords.includes(keyword)) {
    // Check if the keyword exists in our available keywords
    if (allAvailableKeywords.includes(keyword)) {
      selectedFilterKeywords.push(keyword);
      filterInput.value = ""; // Clear input
      renderActiveFilterTags();
      loadResults(1); // Reload results with new filter
    } else {
      alert(`"${keyword}" is not a valid keyword. Please add it first.`);
    }
  } else if (selectedFilterKeywords.includes(keyword)) {
    alert(`"${keyword}" is already applied as a filter.`);
  }
}

// Removes a filter tag
function removeFilterTag(keywordToRemove) {
  selectedFilterKeywords = selectedFilterKeywords.filter(
    (kw) => kw !== keywordToRemove
  );
  renderActiveFilterTags();
  loadResults(1); // Reload results after removing filter
}

// Clears all active filters
function clearAllFilters() {
  selectedFilterKeywords = [];
  renderActiveFilterTags();
  loadResults(1); // Reload results after clearing all filters
}

async function loadResults(page, isAutoRefresh = false) {
  currentPage = page;
  const resultsGrid = document.getElementById("resultsGrid");
  const paginationDiv = document.getElementById("pagination");

  if (!isAutoRefresh) {
    // Only show loading message if it's not an auto-refresh
    resultsGrid.innerHTML = '<p class="loading-message">Loading results...</p>';
    paginationDiv.innerHTML = "";
  }

  const queryParams = new URLSearchParams({ page: page, page_size: 12 });
  if (selectedFilterKeywords.length > 0) {
    queryParams.append("keywords", selectedFilterKeywords.join(","));
  }

  try {
    const data = await fetchApi(`/results/?${queryParams.toString()}`);

    resultsGrid.innerHTML = ""; // Clear existing content (loading message or previous results)

    if (data.items.length === 0) {
      resultsGrid.innerHTML =
        '<p class="empty-results-message">No matching results found.</p>';
      paginationDiv.innerHTML = ""; // Clear pagination if no results
      return;
    }

    data.items.forEach((result) => {
      const card = document.createElement("div");
      card.className = "result-card";
      const publishedDate = result.published_date
        ? new Date(result.published_date).toLocaleDateString()
        : "N/A";
      const matchedKeywordsHtml = result.matched_keywords
        ? result.matched_keywords
            .split(",")
            .map((kw) => `<span>${kw.trim()}</span>`)
            .join("")
        : "";

      card.innerHTML = `
                <h3><a href="${
                  result.link
                }" target="_blank" rel="noopener noreferrer">${
        result.title || "No Title"
      }</a></h3>
                <p>${result.summary || "No summary available."}</p>
                <div class="footer">
                    <div class="matched-keywords">${matchedKeywordsHtml}</div>
                    <div class="published-date">${publishedDate}</div>
                </div>
            `;
      resultsGrid.appendChild(card);
    });

    renderPagination(data.current_page, data.total_pages);
  } catch (error) {
    console.error("Failed to load results:", error);
    resultsGrid.innerHTML =
      '<p class="error-message">Error loading results. Please try again.</p>';
    paginationDiv.innerHTML = ""; // Clear pagination on error
  }
}

function renderPagination(currentPage, totalPages) {
  const paginationDiv = document.getElementById("pagination");
  paginationDiv.innerHTML = "";

  // Previous button
  const prevButton = document.createElement("button");
  prevButton.textContent = "Previous";
  prevButton.disabled = currentPage === 1;
  prevButton.addEventListener("click", () => loadResults(currentPage - 1));
  paginationDiv.appendChild(prevButton);

  // Page numbers (simple version)
  const maxPagesToShow = 5; // e.g., 1 ... 4 5 6 ... 10
  let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
  let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

  if (endPage - startPage + 1 < maxPagesToShow) {
    startPage = Math.max(1, endPage - maxPagesToShow + 1);
  }

  if (startPage > 1) {
    const btn = document.createElement("button");
    btn.textContent = "1";
    btn.addEventListener("click", () => loadResults(1));
    paginationDiv.appendChild(btn);
    if (startPage > 2) {
      const ellipsis = document.createElement("span");
      ellipsis.textContent = "...";
      paginationDiv.appendChild(ellipsis);
    }
  }

  for (let i = startPage; i <= endPage; i++) {
    const button = document.createElement("button");
    button.textContent = i;
    button.classList.toggle("active", i === currentPage);
    button.addEventListener("click", () => loadResults(i));
    paginationDiv.appendChild(button);
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      const ellipsis = document.createElement("span");
      ellipsis.textContent = "...";
      paginationDiv.appendChild(ellipsis);
    }
    const btn = document.createElement("button");
    btn.textContent = totalPages;
    btn.addEventListener("click", () => loadResults(totalPages));
    paginationDiv.appendChild(btn);
  }

  // Next button
  const nextButton = document.createElement("button");
  nextButton.textContent = "Next";
  nextButton.disabled = currentPage === totalPages;
  nextButton.addEventListener("click", () => loadResults(currentPage + 1));
  paginationDiv.appendChild(nextButton);
}
