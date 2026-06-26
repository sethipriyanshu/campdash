import { useEffect, useState } from 'react';
import { getConfig, getMenu, mediaUrl, placeOrder } from './api.js';

export default function App() {
  const [menu, setMenu] = useState(null);
  const [err, setErr] = useState('');
  const [feeBps, setFeeBps] = useState(0);
  const [view, setView] = useState({ name: 'menu' }); // menu | checkout | done

  useEffect(() => {
    getMenu().then(setMenu).catch((e) => setErr(e.message));
    getConfig().then((c) => setFeeBps(c.delivery_fee_bps || 0)).catch(() => {});
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">Camp<span className="logo-dash">Dash</span></span>
        <span className="tag">Made to order, fresh off the grill — delivered by hand (sadly, not a drone).</span>
        <span className="tag tag-makers">From the makers of the best grilled cheese at the Night Market.</span>
      </header>

      {view.name === 'menu' && (
        <Menu menu={menu} err={err} onPick={(item) => setView({ name: 'checkout', item })} />
      )}
      {view.name === 'checkout' && (
        <Checkout
          item={view.item}
          feeBps={feeBps}
          onBack={() => setView({ name: 'menu' })}
          onDone={(order) => setView({ name: 'done', order })}
        />
      )}
      {view.name === 'done' && (
        <Done order={view.order} onMore={() => setView({ name: 'menu' })} />
      )}

      <footer className="footer">
        Orders are delivered electronically. No refunds on vibes.
      </footer>
    </div>
  );
}

function Menu({ menu, err, onPick }) {
  if (err) return <p className="state err">Couldn’t load the menu: {err}</p>;
  if (!menu) return <p className="state">Loading the menu…</p>;
  if (!menu.length) return <p className="state">No food yet. Check back soon.</p>;
  return (
    <main className="menu">
      {menu.map((item) => (
        <button key={item.id} className="card" onClick={() => onPick(item)}>
          {item.photo_path && <img className="card-img" src={mediaUrl(item.photo_path)} alt={item.name} />}
          <div className="card-body">
            <div className="card-row">
              <span className="card-name">{item.name}</span>
              <span className="card-price">{item.price} SB</span>
            </div>
            {item.blurb && <p className="card-blurb">{item.blurb}</p>}
            <span className="card-cta">Order →</span>
          </div>
        </button>
      ))}
    </main>
  );
}

function Checkout({ item, feeBps, onBack, onDone }) {
  const [qty, setQty] = useState(1);
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');
  const [pan, setPan] = useState('');
  const [otp, setOtp] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const subtotal = item.price * qty;
  const feePct = feeBps / 100;
  const fee = Math.round(subtotal * feeBps) / 10000;
  const total = (subtotal + fee).toFixed(2);

  async function pay(e) {
    e.preventDefault();
    setBusy(true);
    setErr('');
    try {
      const order = await placeOrder({
        item_id: item.id, qty, email: email.trim(), address: address.trim(),
        phone: phone.trim() || null, pan: pan.replace(/\s/g, ''), otp: otp.trim(),
      });
      onDone(order);
    } catch (e2) {
      setErr(e2.message || 'Payment failed');
      setBusy(false);
    }
  }

  return (
    <form className="checkout" onSubmit={pay}>
      <button type="button" className="back" onClick={onBack}>← Menu</button>

      <div className="co-item">
        {item.photo_path && <img className="co-img" src={mediaUrl(item.photo_path)} alt={item.name} />}
        <div>
          <div className="co-name">{item.name}</div>
          <div className="co-price">{item.price} SB each</div>
        </div>
      </div>

      <div className="qty">
        <span>Quantity</span>
        <div className="qty-ctl">
          <button type="button" onClick={() => setQty((q) => Math.max(1, q - 1))}>−</button>
          <span className="qty-n">{qty}</span>
          <button type="button" onClick={() => setQty((q) => Math.min(20, q + 1))}>+</button>
        </div>
      </div>

      <label className="field">
        <span>Email (for your order confirmation)</span>
        <input type="email" inputMode="email" placeholder="you@example.com" value={email}
          onChange={(e) => setEmail(e.target.value)} required />
      </label>
      <label className="field">
        <span>Delivery address</span>
        <input type="text" placeholder="Tent 7, Dusty Field B" value={address}
          onChange={(e) => setAddress(e.target.value)} required />
      </label>
      <label className="field">
        <span>Shadytel phone number (optional)</span>
        <input type="tel" inputMode="tel" placeholder="+1 (555) SHADY-00" value={phone}
          onChange={(e) => setPhone(e.target.value)} />
      </label>
      <label className="field">
        <span>ShadyBucks card number</span>
        <input type="text" inputMode="numeric" placeholder="8997…" value={pan}
          onChange={(e) => setPan(e.target.value)} required />
      </label>
      <label className="field">
        <span>One-time code (OTP)</span>
        <input type="text" inputMode="numeric" placeholder="123456" value={otp}
          onChange={(e) => setOtp(e.target.value)} required />
      </label>

      <div className="summary">
        <div className="sum-row"><span>Subtotal</span><span>{subtotal.toFixed(2)} SB</span></div>
        <div className="sum-row"><span>Delivery fee ({feePct.toFixed(0)}%)</span><span>{fee.toFixed(2)} SB</span></div>
        <div className="sum-row sum-total"><span>Total</span><span>{total} SB</span></div>
      </div>

      {err && <p className="err-line">{err}</p>}

      <div className="pay-bar">
        <button className="pay-btn" disabled={busy}>
          {busy ? 'Paying…' : `Pay ${total} SB`}
        </button>
      </div>
    </form>
  );
}

function Done({ order, onMore }) {
  return (
    <main className="done">
      <div className="done-check">✓</div>
      <h2>Order placed!</h2>
      <p>
        Your <b>{order.qty}× {order.item_name}</b> is “on its way” —
        a photo is {order.emailed ? 'in your inbox' : 'being sent'} at <b>{order.email}</b>.
      </p>
      <p className="done-total">Paid {order.total} SB</p>
      {!order.emailed && <p className="done-note">(Email is queued — it’ll arrive shortly.)</p>}
      <button className="more-btn" onClick={onMore}>Order more food</button>
    </main>
  );
}
