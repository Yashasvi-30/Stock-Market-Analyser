document.addEventListener("DOMContentLoaded", () => {
    loadPortfolio();
});

async function loadPortfolio() {
    const res = await fetch("/api/portfolio");
    const data = await res.json();
    const tbody = document.getElementById("portfolio-body");
    tbody.innerHTML = "";

    for (const [ticker, stock] of Object.entries(data)) {
        const row = `
            <tr>
                <td>${ticker}</td>
                <td>${stock.name}</td>
                <td>${stock.shares}</td>
                <td>₹${stock.price}</td>
                <td>₹${(stock.shares * stock.price).toFixed(2)}</td>
                <td><button onclick="removeStock('${ticker}')">🗑️</button></td>
            </tr>
        `;
        tbody.innerHTML += row;
    }
}

async function removeStock(ticker) {
    await fetch(`/api/remove/${ticker}`, { method: "DELETE" });
    loadPortfolio();
}

document.getElementById("save-stock-btn").addEventListener("click", async (e) => {
    e.preventDefault();
    const data = {
        ticker: document.getElementById("stock-symbol").value,
        name: document.getElementById("stock-name").value,
        shares: parseFloat(document.getElementById("stock-shares").value),
        price: parseFloat(document.getElementById("stock-cost").value)
    };

    await fetch("/api/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    loadPortfolio();
    document.getElementById("stock-form").reset();
});
document.getElementById("contact-form").addEventListener("submit", function (e) {
    e.preventDefault();

    const name = document.getElementById("contact-name").value;
    const email = document.getElementById("contact-email").value;
    const message = document.getElementById("contact-message").value;

    document.getElementById("conf-name").textContent = name;
    document.getElementById("conf-email").textContent = email;
    document.getElementById("conf-message").textContent = message;

    document.getElementById("confirm-modal").style.display = "block";
});

function sendConfirmation() {
    closeModal("confirm-modal");
    document.getElementById("sent-modal").style.display = "block";

    // Optionally clear the form
    document.getElementById("contact-form").reset();
}

function closeModal(id) {
    document.getElementById(id).style.display = "none";
}
