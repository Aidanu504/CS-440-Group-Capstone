async function api(url, method = 'GET', body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  try {
    const res = await fetch(url, opts);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error (${url}):`, err);
    alert(`Error: ${err.message}`);
    return null;
  }
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function formatDate(iso) {
  return new Intl.DateTimeFormat('en-US', {
    year:   'numeric',
    month:  'short',
    day:    'numeric',
    hour:   '2-digit',
    minute: '2-digit',
  }).format(new Date(iso));
}

async function loadProducts() {
  const prods = await api('/products');
  if (!prods) return;

  const tbody = document.querySelector('#product-table tbody');
  tbody.innerHTML = '';

  prods.forEach(p => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${p.id}</td>
      <td>${p.name}</td>
      <td>${formatCurrency(p.price)}</td>
      <td>${p.stock}</td>
      <td>
        <button class="btn btn-sm btn-outline-primary view-product" data-id="${p.id}">View</button>
        <button class="btn btn-sm btn-outline-secondary update-stock" data-id="${p.id}">Update Stock</button>
      </td>
    `;
    tbody.appendChild(row);
  });

  document.querySelectorAll('.view-product').forEach(btn => {
    btn.addEventListener('click', async () => {
      const d = await api(`/products/${btn.dataset.id}`);
      if (d) {
        alert(`
Product: ${d.name}
Price: ${formatCurrency(d.price)}
Stock: ${d.stock}
Views: ${d.views || 0}
        `.trim());
      }
    });
  });

  document.querySelectorAll('.update-stock').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      const v  = prompt('Enter new stock level:');
      const n  = parseInt(v, 10);
      if (v !== null && !isNaN(n)) {
        await api(`/products/${id}`, 'PUT', { stock: n });
        loadProducts();
      }
    });
  });

  const histSel = document.getElementById('product-history-select');
  if (histSel) {
    histSel.innerHTML = '<option value="">Select a product</option>';
    prods.forEach(p => {
      histSel.add(new Option(`${p.name}`, p.id));
    });
  }
}

async function loadSuppliers() {
  const supps = await api('/suppliers');
  if (!supps) return;

  const sel = document.getElementById('prod-supplier');
  if (!sel) return;

  sel.innerHTML = '<option value="">Select a supplier</option>';
  supps.forEach(s => sel.add(new Option(s.name, s.id)));
}

async function loadCustomers() {
  const custs = await api('/customers');
  if (!custs) return;

  ['order-customer', 'view-orders-customer'].forEach(id => {
    const sel = document.getElementById(id);
    if (sel) {
      sel.innerHTML = '<option value="">Select a customer</option>';
      custs.forEach(c => sel.add(new Option(c.name, c.id)));
    }
  });
}

async function addCustomerHandler() {
  const name  = document.getElementById('cust-name').value.trim();
  const email = document.getElementById('cust-email').value.trim();
  if (!name || !email) {
    return alert('Please enter both name and email.');
  }

  const res = await api('/customers', 'POST', { name, email });
  if (res && res.id) {
    alert(`Customer created! ID: ${res.id}`);
    document.getElementById('cust-name').value  = '';
    document.getElementById('cust-email').value = '';
    loadCustomers();
  }
}

function addProductLineItem() {
  const container = document.getElementById('order-products');
  const template  = container.querySelector('.product-item');

  if (!template) {
    const div = document.createElement('div');
    div.className = 'product-item mb-2';
    div.innerHTML = `
      <select class="form-select product-select mb-1">
        <option value="">Select a product</option>
      </select>
      <div class="d-flex">
        <input type="number" class="form-control product-qty" min="1" value="1">
        <button class="btn btn-sm btn-light ms-1 remove-product">×</button>
      </div>
    `;
    div.querySelector('.remove-product')
       .addEventListener('click', () => {
         if (container.children.length > 1) div.remove();
       });
    container.appendChild(div);
  }

  const node = container.querySelector('.product-item').cloneNode(true);
  node.querySelector('.product-select').value = '';
  node.querySelector('.product-qty').value   = '1';
  node.querySelector('.remove-product')
      .addEventListener('click', () => {
        if (container.children.length > 1) node.remove();
      });
  container.appendChild(node);

  api('/products').then(prods => {
    container.querySelectorAll('.product-select').forEach(sel => {
      sel.innerHTML = '<option value="">Select a product</option>';
      prods.filter(p => p.stock > 0).forEach(p => {
        sel.add(new Option(`${p.name} (${formatCurrency(p.price)})`, p.id));
      });
    });
  });
}

async function createOrder() {
  const custId = document.getElementById('order-customer').value;
  if (!custId) return alert('Select a customer.');

  const items = [];
  document.querySelectorAll('.product-item').forEach(div => {
    const pid = +div.querySelector('.product-select').value;
    const qty = +div.querySelector('.product-qty').value;
    if (pid && qty > 0) items.push({ product_id: pid, quantity: qty });
  });
  if (!items.length) return alert('Add at least one product.');

  const res = await api('/orders', 'POST', { customer_id: +custId, items });
  if (res) {
    alert(`Order #${res.order_id} created!\nTotal: ${formatCurrency(res.total_amount)}`);
    document.getElementById('order-products').innerHTML = '';
    addProductLineItem();
    document.getElementById('order-customer').value = '';
    loadProducts();
  }
}

async function viewPayment(orderId) {
  const data = await api(`/orders/${orderId}/payment`);
  if (!data || data.error) return alert("No payment found.");

  alert(`Method: ${data.method}
  Amount: ${formatCurrency(data.amount)}
  Status: ${data.status}
  Timestamp: ${formatDate(data.timestamp)}`);
}
async function makePayment(orderId, totalAmount) {
  const amountStr = prompt("Enter payment amount:");
  const amount = parseFloat(amountStr);
  if (isNaN(amount) || amount <= 0) return alert("Invalid amount.");

  const method = prompt("Payment method (e.g., Cash, Credit Card):") || "Cash";
  const status = amount >= totalAmount ? "Paid" : "Pending";

  const res = await api(`/orders/${orderId}/pay`, "POST", {
    amount,
    method,
    status,
  });

  if (res?.message) {
    alert("Payment recorded!");
  } else {
    alert("Error recording payment.");
  }
}

async function viewCustomerOrders() {
  const custId = document.getElementById('view-orders-customer').value;
  if (!custId) return alert('Select a customer.');

  const orders = await api(`/orders/${custId}`);
  const container = document.getElementById('orders-container');

  if (!orders || !orders.length) {
    container.innerHTML = '<p>No orders found.</p>';
    return;
  }

  let html = '<div class="accordion" id="orderAccordion">';
  orders.forEach((o, i) => {
    html += `
      <div class="accordion-item">
        <h2 class="accordion-header">
          <button class="accordion-button collapsed"
                  type="button"
                  data-bs-toggle="collapse"
                  data-bs-target="#order${i}">
            Order #${o._id} — ${formatDate(o.date)} — ${formatCurrency(o.total_amount)}
          </button>
        </h2>
        <div id="order${i}" class="accordion-collapse collapse" data-bs-parent="#orderAccordion">
          <div class="accordion-body">
            <p><strong>Status:</strong> ${o.status || 'Processing'}</p>
            <p>
              <strong>Payment:</strong>
              <button class="btn btn-sm btn-outline-info" onclick="viewPayment('${o._id}')">View Payment</button>
            </p>
            <p>
              <strong>Make Payment:</strong>
              <button class="btn btn-sm btn-outline-success" onclick="makePayment('${o._id}', ${o.total_amount})">Pay</button>
            </p>
            <table class="table table-sm">
              <thead>
                <tr><th>Product</th><th>Price</th><th>Qty</th><th>Subtotal</th></tr>
              </thead>
              <tbody>
                ${o.items.map(it => `
                  <tr>
                    <td>${it.name}</td>
                    <td>${formatCurrency(it.price)}</td>
                    <td>${it.quantity}</td>
                    <td>${formatCurrency(it.price * it.quantity)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  });
  html += '</div>';
  container.innerHTML = html;
}

async function getCachedProduct() {
  const pid = document.getElementById('cache-product-id').value;
  if (!pid) return alert('Enter product ID.');

  const p = await api(`/products/${pid}`);
  if (p) {
    document.getElementById('cache-result').textContent = JSON.stringify(p, null, 2);
  }
}

async function invalidateCache() {
  await loadProducts();
  const el = document.getElementById('cache-result');
  el.textContent = 'Cache invalidated!';
  setTimeout(() => { el.textContent = 'No data requested yet.'; }, 3000);
}

async function loadPopularProducts() {
  const list = await api('/analytics/popular-products');
  const c = document.getElementById('popular-products-container');
  if (!list || !list.length) return c.innerHTML = '<p>No data.</p>';

  let html = '<div class="list-group">';
  list.forEach(p => {
    html += `
      <div class="list-group-item">
        <div class="d-flex justify-content-between">
          <strong>${p.name}</strong>
          <span>Views: ${p.views || 0}</span>
        </div>
        <small>Price: ${formatCurrency(p.price)} | Stock: ${p.stock}</small>
      </div>
    `;
  });
  html += '</div>';
  c.innerHTML = html;
}

let salesChart = null;
let productHistoryChart = null;

async function loadSalesAnalytics() {
  const days = document.getElementById('sales-timeframe').value;
  const data = await api(`/analytics/sales?days=${days}`);
  if (!data?.sales_data?.length) return alert('No sales data.');

  const labels = data.sales_data.map(d => new Date(d.time).toLocaleDateString());
  const vals   = data.sales_data.map(d => d.total_sales);

  const ctx = document.getElementById('sales-chart').getContext('2d');
  salesChart?.destroy();
  salesChart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label: 'Daily Sales', data: vals, fill: false, tension: 0.1 }] },
    options: { responsive: true, scales: { y: { beginAtZero: true } } },
  });
}

async function loadProductSalesHistory() {
  const pid = document.getElementById('product-history-select').value;
  if (!pid) return alert('Select a product.');

  const data = await api(`/analytics/product-history/${pid}`);
  if (!data?.sales_history?.length) return alert('No history.');

  const labels = data.sales_history.map(d => new Date(d.time).toLocaleDateString());
  const vals   = data.sales_history.map(d => d.sales);

  const ctx = document.getElementById('product-history-chart').getContext('2d');
  productHistoryChart?.destroy();
  productHistoryChart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Total price Sold', data: vals, borderWidth: 1 }] },
    options: { responsive: true, scales: { y: { beginAtZero: true } } },
  });
}

function setupEventListeners() {
  document.getElementById('btn-add-prod')?.addEventListener('click', async () => {
    await api('/products', 'POST', {
      name:        document.getElementById('prod-name').value,
      price:       +document.getElementById('prod-price').value,
      stock:       +document.getElementById('prod-stock').value,
      supplier_id: +document.getElementById('prod-supplier').value,
    });
    loadProducts();
  });

  document.getElementById('btn-add-sup')?.addEventListener('click', async () => {
    await api('/suppliers', 'POST', { name: document.getElementById('sup-name').value });
    loadSuppliers();
  });

  document.getElementById('btn-add-cust')?.addEventListener('click', addCustomerHandler);

  document.getElementById('btn-add-product-line')?.addEventListener('click', addProductLineItem);
  document.getElementById('btn-create-order')?.addEventListener('click', createOrder);
  document.getElementById('btn-view-orders')?.addEventListener('click', viewCustomerOrders);

  document.getElementById('btn-get-cached-product')?.addEventListener('click', getCachedProduct);
  document.getElementById('btn-invalidate-cache')?.addEventListener('click', invalidateCache);
  document.getElementById('btn-popular-products')?.addEventListener('click', loadPopularProducts);

  document.getElementById('btn-sales-analytics')?.addEventListener('click', loadSalesAnalytics);
  document.getElementById('btn-product-history')?.addEventListener('click', loadProductSalesHistory);
}

window.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await loadProducts();
  await loadSuppliers();
  await loadCustomers();
  addProductLineItem();
});
