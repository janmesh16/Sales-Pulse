/**
 * SalesPulse POS Terminal (Billing Engine)
 * Handles fast barcode/text product search, interactive cart management,
 * live discount & tax calculations, and transactional checkout.
 */

class BillingTerminal {
  constructor() {
    this.cart = [];
    this.discountType = 'fixed'; // 'fixed' (₹) or 'percent' (%)
    this.discountValue = 0;
    this.paymentMode = 'CASH';

    this.searchInput = document.getElementById('productSearchInput');
    this.searchResults = document.getElementById('searchResults');
    this.cartTableBody = document.getElementById('cartTableBody');
    this.emptyCartMsg = document.getElementById('emptyCartMsg');
    this.subtotalEl = document.getElementById('cartSubtotal');
    this.discountAmountEl = document.getElementById('cartDiscountAmount');
    this.totalPayableEl = document.getElementById('cartTotalPayable');
    this.discountInput = document.getElementById('discountInput');
    this.checkoutBtn = document.getElementById('checkoutBtn');
    this.checkoutError = document.getElementById('checkoutError');

    this.init();
  }

  init() {
    // Search listener with debounce
    let debounceTimer;
    this.searchInput?.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      const query = e.target.value.trim();
      if (query.length < 1) {
        this.hideSearchResults();
        return;
      }
      debounceTimer = setTimeout(() => this.searchProducts(query), 200);
    });

    // Close search dropdown on click outside
    document.addEventListener('click', (e) => {
      if (!this.searchInput?.contains(e.target) && !this.searchResults?.contains(e.target)) {
        this.hideSearchResults();
      }
    });

    // Quick add product cards
    document.querySelectorAll('.quick-add-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const product = {
          product_id: parseInt(btn.dataset.id),
          sku: btn.dataset.sku,
          name: btn.dataset.name,
          sell_price: parseFloat(btn.dataset.price),
          stock_qty: parseInt(btn.dataset.stock)
        };
        this.addToCart(product);
      });
    });

    // Discount change
    this.discountInput?.addEventListener('input', () => {
      this.discountValue = parseFloat(this.discountInput.value) || 0;
      this.renderTotals();
    });

    document.querySelectorAll('input[name="discountType"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.discountType = e.target.value;
        this.renderTotals();
      });
    });

    // Payment mode selector
    document.querySelectorAll('input[name="paymentMode"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.paymentMode = e.target.value;
      });
    });

    // Checkout submission
    this.checkoutBtn?.addEventListener('click', () => this.handleCheckout());
  }

  async searchProducts(query) {
    try {
      const res = await fetch(`/products/api/search?q=${encodeURIComponent(query)}`);
      const products = await res.json();
      this.renderSearchResults(products);
    } catch (err) {
      console.error('Search error:', err);
    }
  }

  renderSearchResults(products) {
    if (!this.searchResults) return;

    if (!products || products.length === 0) {
      this.searchResults.innerHTML = '<div class="p-3 text-muted text-center small">No matching products found</div>';
      this.searchResults.classList.remove('d-none');
      return;
    }

    let html = '<div class="list-group list-group-flush">';
    products.forEach(p => {
      const stockBadge = p.stock_qty > 0 
        ? `<span class="badge bg-success-subtle text-success">${p.stock_qty} in stock</span>`
        : `<span class="badge bg-danger-subtle text-danger">Out of stock</span>`;

      html += `
        <button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-2 search-item" 
          data-id="${p.product_id}" data-name="${p.name}" data-sku="${p.sku}" data-price="${p.sell_price}" data-stock="${p.stock_qty}">
          <div>
            <div class="fw-semibold text-dark">${p.name}</div>
            <div class="small text-muted">SKU: ${p.sku}</div>
          </div>
          <div class="text-end">
            <div class="fw-bold text-teal">₹ ${p.sell_price.toFixed(2)}</div>
            ${stockBadge}
          </div>
        </button>
      `;
    });
    html += '</div>';

    this.searchResults.innerHTML = html;
    this.searchResults.classList.remove('d-none');

    // Attach click events
    this.searchResults.querySelectorAll('.search-item').forEach(item => {
      item.addEventListener('click', () => {
        const p = {
          product_id: parseInt(item.dataset.id),
          sku: item.dataset.sku,
          name: item.dataset.name,
          sell_price: parseFloat(item.dataset.price),
          stock_qty: parseInt(item.dataset.stock)
        };
        this.addToCart(p);
        this.hideSearchResults();
        if (this.searchInput) this.searchInput.value = '';
      });
    });
  }

  hideSearchResults() {
    this.searchResults?.classList.add('d-none');
  }

  addToCart(product) {
    if (product.stock_qty <= 0) {
      alert(`Cannot add "${product.name}". Product is currently out of stock.`);
      return;
    }

    const existing = this.cart.find(item => item.product_id === product.product_id);
    if (existing) {
      if (existing.qty + 1 > product.stock_qty) {
        alert(`Cannot add more. Available stock for "${product.name}" is ${product.stock_qty}.`);
        return;
      }
      existing.qty += 1;
    } else {
      this.cart.push({ ...product, qty: 1 });
    }

    this.renderCart();
  }

  updateQty(productId, newQty) {
    const item = this.cart.find(i => i.product_id === productId);
    if (!item) return;

    if (newQty <= 0) {
      this.removeFromCart(productId);
      return;
    }

    if (newQty > item.stock_qty) {
      alert(`Available stock for "${item.name}" is only ${item.stock_qty}.`);
      return;
    }

    item.qty = newQty;
    this.renderCart();
  }

  removeFromCart(productId) {
    this.cart = this.cart.filter(item => item.product_id !== productId);
    this.renderCart();
  }

  clearCart() {
    this.cart = [];
    this.discountValue = 0;
    if (this.discountInput) this.discountInput.value = '';
    this.renderCart();
  }

  renderCart() {
    if (!this.cartTableBody) return;

    if (this.cart.length === 0) {
      this.cartTableBody.innerHTML = '';
      this.emptyCartMsg?.classList.remove('d-none');
      if (this.checkoutBtn) this.checkoutBtn.disabled = true;
      this.renderTotals();
      return;
    }

    this.emptyCartMsg?.classList.add('d-none');
    if (this.checkoutBtn) this.checkoutBtn.disabled = false;

    let html = '';
    this.cart.forEach(item => {
      const lineTotal = item.sell_price * item.qty;
      html += `
        <tr>
          <td class="py-2">
            <div class="fw-semibold text-truncate" style="max-width: 140px;" title="${item.name}">${item.name}</div>
            <span class="small text-muted">${item.sku}</span>
          </td>
          <td class="text-end py-2">₹ ${item.sell_price.toFixed(2)}</td>
          <td class="py-2">
            <div class="input-group input-group-sm" style="width: 100px;">
              <button class="btn btn-outline-secondary btn-qty-minus" data-id="${item.product_id}" type="button">-</button>
              <input type="number" class="form-control text-center p-1 item-qty-input" data-id="${item.product_id}" value="${item.qty}" min="1" max="${item.stock_qty}">
              <button class="btn btn-outline-secondary btn-qty-plus" data-id="${item.product_id}" type="button">+</button>
            </div>
          </td>
          <td class="text-end fw-semibold py-2">₹ ${lineTotal.toFixed(2)}</td>
          <td class="text-center py-2">
            <button class="btn btn-sm text-danger border-0 p-1 btn-remove-item" data-id="${item.product_id}" title="Remove">
              <i class="bi bi-trash3"></i>
            </button>
          </td>
        </tr>
      `;
    });

    this.cartTableBody.innerHTML = html;

    // Attach row events
    this.cartTableBody.querySelectorAll('.btn-qty-minus').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt(btn.dataset.id);
        const it = this.cart.find(i => i.product_id === id);
        if (it) this.updateQty(id, it.qty - 1);
      });
    });

    this.cartTableBody.querySelectorAll('.btn-qty-plus').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt(btn.dataset.id);
        const it = this.cart.find(i => i.product_id === id);
        if (it) this.updateQty(id, it.qty + 1);
      });
    });

    this.cartTableBody.querySelectorAll('.item-qty-input').forEach(input => {
      input.addEventListener('change', () => {
        const id = parseInt(input.dataset.id);
        const val = parseInt(input.value) || 1;
        this.updateQty(id, val);
      });
    });

    this.cartTableBody.querySelectorAll('.btn-remove-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = parseInt(btn.dataset.id);
        this.removeFromCart(id);
      });
    });

    this.renderTotals();
  }

  renderTotals() {
    const subtotal = this.cart.reduce((sum, item) => sum + (item.sell_price * item.qty), 0);
    
    let discountAmount = 0;
    if (this.discountType === 'percent') {
      discountAmount = (subtotal * Math.min(100, Math.max(0, this.discountValue))) / 100;
    } else {
      discountAmount = Math.min(subtotal, Math.max(0, this.discountValue));
    }

    const totalPayable = Math.max(0, subtotal - discountAmount);

    if (this.subtotalEl) this.subtotalEl.textContent = `₹ ${subtotal.toFixed(2)}`;
    if (this.discountAmountEl) this.discountAmountEl.textContent = `- ₹ ${discountAmount.toFixed(2)}`;
    if (this.totalPayableEl) this.totalPayableEl.textContent = `₹ ${totalPayable.toFixed(2)}`;
  }

  async handleCheckout() {
    if (this.cart.length === 0) {
      alert('Cart is empty.');
      return;
    }

    const subtotal = this.cart.reduce((sum, item) => sum + (item.sell_price * item.qty), 0);
    let discountAmount = 0;
    if (this.discountType === 'percent') {
      discountAmount = (subtotal * Math.min(100, Math.max(0, this.discountValue))) / 100;
    } else {
      discountAmount = Math.min(subtotal, Math.max(0, this.discountValue));
    }

    const customerName = document.getElementById('customerName')?.value.trim() || '';
    const customerPhone = document.getElementById('customerPhone')?.value.trim() || '';

    const payload = {
      cart: this.cart.map(i => ({ product_id: i.product_id, qty: i.qty })),
      discount: discountAmount,
      payment_mode: this.paymentMode,
      customer_name: customerName,
      customer_phone: customerPhone
    };

    if (this.checkoutBtn) {
      this.checkoutBtn.disabled = true;
      this.checkoutBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
    }
    if (this.checkoutError) {
      this.checkoutError.classList.add('d-none');
    }

    try {
      const response = await apiFetch('/sales/create', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      const data = await response.json();

      if (data.success) {
        window.location.href = data.redirect_url;
      } else {
        throw new Error(data.error || 'Failed to complete transaction.');
      }
    } catch (err) {
      if (this.checkoutError) {
        this.checkoutError.textContent = err.message;
        this.checkoutError.classList.remove('d-none');
      } else {
        alert(err.message);
      }
      if (this.checkoutBtn) {
        this.checkoutBtn.disabled = false;
        this.checkoutBtn.innerHTML = '<i class="bi bi-check2-circle me-1"></i> Complete & Print Receipt';
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('productSearchInput')) {
    window.terminal = new BillingTerminal();
  }
});
