const cart = {};
const products = Object.fromEntries(window.PRODUCTS.map(p => [p[0], {id: p[0], name: p[1], category: p[3], price: p[4], emoji: p[5], stock: p[6]}]));
const drawer = document.querySelector('#cart-drawer');
const overlay = document.querySelector('#overlay');
const accountDialog = document.querySelector('#account-dialog');
const checkoutDialog = document.querySelector('#checkout-dialog');
const paymentDialog = document.querySelector('#payment-dialog');
const paymentConfirmationDialog = document.querySelector('#payment-confirmation-dialog');
const ordersDialog = document.querySelector('#orders-dialog');
const money = value => `₹${value.toFixed(2)}`;
let paymentTimer;
let pendingCheckout;

function openCart() { drawer.classList.add('open'); overlay.classList.add('open'); drawer.setAttribute('aria-hidden', 'false'); }
function closeCart() { drawer.classList.remove('open'); overlay.classList.remove('open'); drawer.setAttribute('aria-hidden', 'true'); }
function renderCart() {
  const entries = Object.values(cart);
  const count = entries.reduce((sum, item) => sum + item.quantity, 0);
  const total = entries.reduce((sum, item) => sum + item.quantity * item.price, 0);
  document.querySelector('#cart-count').textContent = count;
  document.querySelector('#cart-total').textContent = money(total);
  document.querySelector('#checkout-button').disabled = !entries.length;
  document.querySelector('#cart-items').innerHTML = entries.length ? entries.map(item => `<div class="cart-line"><span class="emoji">${item.emoji}</span><div><h3>${item.name}</h3><small>${money(item.price)} each</small><div class="qty"><button data-action="decrease" data-id="${item.id}">−</button><span>${item.quantity}</span><button data-action="increase" data-id="${item.id}" ${item.quantity >= item.stock ? 'disabled' : ''}>+</button></div></div><span class="line-price">${money(item.price * item.quantity)}</span></div>`).join('') : '<p class="empty-state">Your cart is waiting for something delicious.</p>';
}
function add(id) {
  const item = cart[id];
  if (item && item.quantity >= products[id].stock) return;
  if (item) item.quantity += 1;
  else cart[id] = {...products[id], quantity: 1};
  renderCart();
  openCart();
}
function filterProducts() {
  const term = document.querySelector('#search').value.toLowerCase();
  const category = document.querySelector('.filter.active').dataset.category;
  document.querySelectorAll('.product').forEach(card => { card.style.display = (category === 'All' || card.dataset.category === category) && card.dataset.name.toLowerCase().includes(term) ? 'block' : 'none'; });
}
function showAccount() {
  if (window.CURRENT_USER) {
    document.querySelector('#auth-panel').hidden = true;
    document.querySelector('#profile-panel').hidden = false;
    document.querySelector('#profile-name').value = window.CURRENT_USER.name;
    document.querySelector('#profile-address').value = window.CURRENT_USER.address;
  } else {
    document.querySelector('#auth-panel').hidden = false;
    document.querySelector('#profile-panel').hidden = true;
  }
  accountDialog.showModal();
}
async function loadOrders() {
  const target = document.querySelector('#orders-list');
  const response = await fetch('/api/orders');
  const result = await response.json();
  if (!response.ok) { target.innerHTML = `<p class="empty-state">${result.error}</p>`; return; }
  target.innerHTML = result.orders.length ? result.orders.map(order => `<article class="order-card"><div><strong>Order #${order.id}</strong><span>${new Date(order.created_at + 'Z').toLocaleDateString('en-IN')}</span></div><p>${order.status}</p><strong>${money(order.total)}</strong></article>`).join('') : '<p class="empty-state">No orders yet. Your first basket is waiting.</p>';
}
function openOrders() {
  if (!window.CURRENT_USER) { showAccount(); document.querySelector('#auth-message').textContent = 'Sign in to track your orders.'; return; }
  ordersDialog.showModal();
  loadOrders();
}

document.querySelectorAll('.add-button').forEach(button => button.addEventListener('click', () => add(button.dataset.id)));
document.querySelector('#cart-items').addEventListener('click', event => { const button = event.target.closest('button'); if (!button) return; const item = cart[button.dataset.id]; if (!item) return; if (button.dataset.action === 'increase') add(button.dataset.id); else { item.quantity -= 1; if (item.quantity < 1) delete cart[button.dataset.id]; renderCart(); } });
document.querySelector('#cart-button').addEventListener('click', openCart);
document.querySelector('#close-cart').addEventListener('click', closeCart);
overlay.addEventListener('click', closeCart);
document.querySelector('#account-button').addEventListener('click', showAccount);
document.querySelector('#close-account').addEventListener('click', () => accountDialog.close());
document.querySelector('#filters').addEventListener('click', event => { const button = event.target.closest('.filter'); if (!button) return; document.querySelectorAll('.filter').forEach(b => b.classList.remove('active')); button.classList.add('active'); filterProducts(); });
document.querySelector('#search').addEventListener('input', filterProducts);

document.querySelector('#checkout-button').addEventListener('click', () => {
  if (!window.CURRENT_USER) { showAccount(); document.querySelector('#auth-message').textContent = 'Sign in or create an account before checkout.'; return; }
  document.querySelector('#checkout-name').value = window.CURRENT_USER.name;
  document.querySelector('#checkout-address').value = window.CURRENT_USER.address;
  checkoutDialog.showModal();
});
document.querySelector('#close-dialog').addEventListener('click', () => checkoutDialog.close());
document.querySelector('#checkout-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(event.target);
  const total = Object.values(cart).reduce((sum, item) => sum + item.quantity * item.price, 0);
  document.querySelector('#payment-total').textContent = money(total);
  pendingCheckout = {customer: form.get('customer'), address: form.get('address'), items: Object.values(cart).map(item => ({product_id: item.id, quantity: item.quantity})), reference: `FC${Date.now()}`};
  document.querySelector('#qr-code').src = `/api/payment/qr?reference=${encodeURIComponent(pendingCheckout.reference)}&amount=${total.toFixed(2)}`;
  checkoutDialog.close();
  paymentDialog.showModal();
  let seconds = 3;
  document.querySelector('#payment-countdown').textContent = `Confirming payment in ${seconds} seconds...`;
  clearInterval(paymentTimer);
  paymentTimer = setInterval(async () => {
    seconds -= 1;
    if (seconds > 0) { document.querySelector('#payment-countdown').textContent = `Confirming payment in ${seconds} seconds...`; return; }
    clearInterval(paymentTimer);
    const response = await fetch('/api/orders', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...pendingCheckout, payment_method: 'demo_card'})});
    const result = await response.json();
    document.querySelector('#payment-countdown').textContent = '';
    if (response.ok) {
      Object.keys(cart).forEach(key => delete cart[key]);
      renderCart();
      document.querySelector('#confirmation-copy').textContent = `Payment confirmed for ₹${result.total.toFixed(2)}. Your order #${result.order_id} is being prepared.`;
      paymentDialog.close();
      paymentConfirmationDialog.showModal();
    } else {
      document.querySelector('#payment-countdown').textContent = result.error;
    }
  }, 1000);
});
function cancelPayment() { clearInterval(paymentTimer); pendingCheckout = null; document.querySelector('#payment-message').textContent = 'Payment cancelled. Your cart is still saved.'; setTimeout(() => paymentDialog.close(), 900); }
document.querySelector('#close-payment').addEventListener('click', cancelPayment);
document.querySelector('#cancel-payment').addEventListener('click', cancelPayment);
document.querySelector('#close-confirmation').addEventListener('click', () => paymentConfirmationDialog.close());
document.querySelector('#confirmation-orders').addEventListener('click', () => { paymentConfirmationDialog.close(); openOrders(); });
document.querySelector('#orders-button').addEventListener('click', openOrders);
document.querySelector('#close-orders').addEventListener('click', () => ordersDialog.close());

let signupMode = false;
document.querySelector('#auth-switch').addEventListener('click', () => { signupMode = !signupMode; document.querySelector('#auth-title').textContent = signupMode ? 'Create account' : 'Sign in'; document.querySelector('#auth-submit').textContent = signupMode ? 'Create account' : 'Sign in'; document.querySelector('#auth-switch').textContent = signupMode ? 'I already have an account' : 'Create an account'; document.querySelector('#signup-name-wrap').hidden = !signupMode; document.querySelector('#signup-address-wrap').hidden = !signupMode; });
document.querySelector('#auth-form').addEventListener('submit', async event => { event.preventDefault(); const form = new FormData(event.target); const response = await fetch(signupMode ? '/api/auth/signup' : '/api/auth/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(Object.fromEntries(form))}); const result = await response.json(); if (!response.ok) { document.querySelector('#auth-message').textContent = result.error; return; } window.location.reload(); });
document.querySelector('#profile-form').addEventListener('submit', async event => { event.preventDefault(); const response = await fetch('/api/profile', {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(Object.fromEntries(new FormData(event.target)))}); const result = await response.json(); document.querySelector('#profile-message').textContent = response.ok ? 'Profile saved.' : result.error; if (response.ok) window.CURRENT_USER = result.user; });
document.querySelectorAll('.profile-tab').forEach(tab => tab.addEventListener('click', () => { document.querySelectorAll('.profile-tab').forEach(item => item.classList.remove('active')); document.querySelectorAll('.profile-section').forEach(panel => { panel.hidden = panel.id !== tab.dataset.panel; }); tab.classList.add('active'); }));
document.querySelector('#logout-button').addEventListener('click', async () => { await fetch('/api/auth/logout', {method: 'POST'}); window.location.reload(); });
renderCart();
