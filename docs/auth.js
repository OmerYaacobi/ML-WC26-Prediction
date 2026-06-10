/* WC26 Auth + League — localStorage (default) or Firebase (when configured) */
"use strict";

const STARTING_TOKENS = 10000;
const REGISTRY_KEY = "wc26-user-registry";
const SESSION_KEY = "wc26-session";

let firebaseApp = null;
let firebaseAuth = null;
let firestore = null;
let currentUser = null;
const listeners = [];

function emit() {
  listeners.forEach((fn) => fn(currentUser));
}

function hashPassword(pw) {
  let h = 0;
  for (let i = 0; i < pw.length; i++) h = ((h << 5) - h + pw.charCodeAt(i)) | 0;
  return `h${Math.abs(h)}`;
}

function loadRegistry() {
  try {
    return JSON.parse(localStorage.getItem(REGISTRY_KEY) || '{"users":[]}');
  } catch {
    return { users: [] };
  }
}

function saveRegistry(reg) {
  localStorage.setItem(REGISTRY_KEY, JSON.stringify(reg));
}

function useFirebase() {
  return FIREBASE_CONFIG.enabled && FIREBASE_CONFIG.apiKey && FIREBASE_CONFIG.projectId;
}

function mapFirebaseError(err) {
  const messages = {
    "auth/email-already-in-use": "That email is already registered. Switch to Log in and use the same password.",
    "auth/invalid-credential": "Invalid email or password.",
    "auth/wrong-password": "Invalid email or password.",
    "auth/user-not-found": "Invalid email or password.",
    "auth/weak-password": "Password must be at least 6 characters.",
    "auth/invalid-email": "Enter a valid email.",
    "permission-denied":
      "Firestore blocked the request. In Firebase Console → Firestore Database → Rules, paste the rules from firestore.rules and click Publish.",
  };
  const msg = messages[err?.code] || err?.message || "Something went wrong.";
  throw new Error(msg);
}

async function ensureAuthToken(user) {
  await firebaseAuth.authStateReady();
  if (user) await user.getIdToken(true);
}

async function initFirebase() {
  if (!useFirebase() || firebaseApp) return;
  const { initializeApp } = await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js");
  const { getAuth, onAuthStateChanged } = await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js");
  const { getFirestore, doc, getDoc, setDoc, collection, query, where, orderBy, limit, getDocs } =
    await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js");

  firebaseApp = initializeApp(FIREBASE_CONFIG);
  firebaseAuth = getAuth(firebaseApp);
  firestore = getFirestore(firebaseApp);

  window._fb = { doc, getDoc, setDoc, collection, query, where, orderBy, limit, getDocs };

  onAuthStateChanged(firebaseAuth, async (fbUser) => {
    if (!fbUser) {
      currentUser = null;
      emit();
      return;
    }
    try {
      await ensureAuthToken(fbUser);
      const snap = await getDoc(doc(firestore, "users", fbUser.uid));
      if (snap.exists()) {
        currentUser = { id: fbUser.uid, ...snap.data() };
      } else {
        currentUser = {
          id: fbUser.uid,
          username: fbUser.email.split("@")[0],
          email: fbUser.email,
          tokens: STARTING_TOKENS,
        };
        await setDoc(doc(firestore, "users", fbUser.uid), {
          username: currentUser.username,
          email: currentUser.email,
          tokens: STARTING_TOKENS,
          createdAt: Date.now(),
        });
      }
      emit();
    } catch (err) {
      console.error("Firebase profile sync failed:", err);
    }
  });
}

function initLocal() {
  const sessionId = localStorage.getItem(SESSION_KEY);
  if (sessionId) {
    const reg = loadRegistry();
    currentUser = reg.users.find((u) => u.id === sessionId) || null;
    if (!currentUser) localStorage.removeItem(SESSION_KEY);
  }
  emit();
}

async function signupLocal(username, email, password) {
  const reg = loadRegistry();
  const uname = username.trim();
  const mail = email.trim().toLowerCase();
  if (!uname || uname.length < 3) throw new Error("Username must be at least 3 characters.");
  if (!mail.includes("@")) throw new Error("Enter a valid email.");
  if (password.length < 6) throw new Error("Password must be at least 6 characters.");
  if (reg.users.some((u) => u.username.toLowerCase() === uname.toLowerCase()))
    throw new Error("Username already taken.");
  if (reg.users.some((u) => u.email === mail)) throw new Error("Email already registered.");

  const user = {
    id: `u_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    username: uname,
    email: mail,
    passwordHash: hashPassword(password),
    tokens: STARTING_TOKENS,
    createdAt: Date.now(),
    bets: [],
  };
  reg.users.push(user);
  saveRegistry(reg);
  localStorage.setItem(SESSION_KEY, user.id);
  currentUser = { ...user };
  delete currentUser.passwordHash;
  emit();
  return currentUser;
}

async function loginLocal(email, password) {
  const mail = email.trim().toLowerCase();
  const reg = loadRegistry();
  const user = reg.users.find((u) => u.email === mail && u.passwordHash === hashPassword(password));
  if (!user) throw new Error("Invalid email or password.");
  localStorage.setItem(SESSION_KEY, user.id);
  currentUser = { ...user };
  delete currentUser.passwordHash;
  emit();
  return currentUser;
}

async function signupFirebase(username, email, password) {
  const { createUserWithEmailAndPassword, deleteUser } = await import(
    "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js"
  );
  const { doc, setDoc, collection, query, where, getDocs } = window._fb;

  const uname = username.trim();
  if (!uname || uname.length < 3) throw new Error("Username must be at least 3 characters.");

  let cred;
  try {
    cred = await createUserWithEmailAndPassword(firebaseAuth, email.trim(), password);
  } catch (err) {
    mapFirebaseError(err);
  }

  try {
    await ensureAuthToken(cred.user);
    const taken = await getDocs(query(collection(firestore, "users"), where("username", "==", uname)));
    if (!taken.empty) {
      await deleteUser(cred.user);
      throw new Error("Username already taken.");
    }
    const profile = {
      username: uname,
      email: email.trim().toLowerCase(),
      tokens: STARTING_TOKENS,
      createdAt: Date.now(),
      bets: [],
    };
    await setDoc(doc(firestore, "users", cred.user.uid), profile);
    currentUser = { id: cred.user.uid, ...profile };
    emit();
    return currentUser;
  } catch (err) {
    if (err.message === "Username already taken.") throw err;
    mapFirebaseError(err);
  }
}

async function loginFirebase(email, password) {
  const { signInWithEmailAndPassword } = await import("https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js");
  const { doc, getDoc, setDoc } = window._fb;

  let cred;
  try {
    cred = await signInWithEmailAndPassword(firebaseAuth, email.trim(), password);
  } catch (err) {
    mapFirebaseError(err);
  }

  try {
    await ensureAuthToken(cred.user);
    const ref = doc(firestore, "users", cred.user.uid);
    const snap = await getDoc(ref);
    if (snap.exists()) {
      currentUser = { id: cred.user.uid, ...snap.data() };
    } else {
      const profile = {
        username: cred.user.email.split("@")[0],
        email: cred.user.email,
        tokens: STARTING_TOKENS,
        createdAt: Date.now(),
        bets: [],
      };
      await setDoc(ref, profile);
      currentUser = { id: cred.user.uid, ...profile };
    }
    emit();
    return currentUser;
  } catch (err) {
    mapFirebaseError(err);
  }
}

async function getLeaderboardLocal() {
  const reg = loadRegistry();
  return reg.users
    .map((u) => ({ username: u.username, tokens: u.tokens, id: u.id }))
    .sort((a, b) => b.tokens - a.tokens);
}

async function getLeaderboardFirebase() {
  const { collection, query, orderBy, limit, getDocs } = window._fb;
  const snap = await getDocs(query(collection(firestore, "users"), orderBy("tokens", "desc"), limit(50)));
  return snap.docs.map((d) => ({ id: d.id, ...d.data() }));
}

async function updateTokensLocal(delta, betRecord) {
  if (!currentUser) return;
  const reg = loadRegistry();
  const idx = reg.users.findIndex((u) => u.id === currentUser.id);
  if (idx < 0) return;
  reg.users[idx].tokens = Math.max(0, reg.users[idx].tokens + delta);
  if (betRecord) {
    reg.users[idx].bets = reg.users[idx].bets || [];
    reg.users[idx].bets.unshift(betRecord);
  }
  saveRegistry(reg);
  currentUser = { ...reg.users[idx] };
  delete currentUser.passwordHash;
  emit();
}

async function updateTokensFirebase(delta, betRecord) {
  if (!currentUser) return;
  const { doc, getDoc, setDoc } = window._fb;
  const ref = doc(firestore, "users", currentUser.id);
  const snap = await getDoc(ref);
  const data = snap.data();
  const tokens = Math.max(0, (data.tokens || 0) + delta);
  const bets = data.bets || [];
  if (betRecord) bets.unshift(betRecord);
  await setDoc(ref, { ...data, tokens, bets }, { merge: true });
  currentUser = { ...currentUser, tokens, bets };
  emit();
}

window.WC26Auth = {
  STARTING_TOKENS,
  isCloud: () => useFirebase(),

  async init() {
    if (useFirebase()) await initFirebase();
    else initLocal();
  },

  onChange(fn) {
    listeners.push(fn);
    if (currentUser !== undefined) fn(currentUser);
  },

  getUser() {
    return currentUser;
  },

  async signup(username, email, password) {
    if (useFirebase()) return signupFirebase(username, email, password);
    return signupLocal(username, email, password);
  },

  async login(email, password) {
    if (useFirebase()) return loginFirebase(email, password);
    return loginLocal(email, password);
  },

  logout() {
    if (useFirebase() && firebaseAuth) {
      import("https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js").then(({ signOut }) =>
        signOut(firebaseAuth)
      );
      return;
    }
    localStorage.removeItem(SESSION_KEY);
    currentUser = null;
    emit();
  },

  async getLeaderboard() {
    if (useFirebase()) return getLeaderboardFirebase();
    return getLeaderboardLocal();
  },

  async placeBet(stake, slip, totalOdds) {
    if (!currentUser) throw new Error("Log in to place a bet.");
    if (stake <= 0) throw new Error("Enter a stake greater than 0.");
    if (!slip.length) throw new Error("Your slip is empty.");
    if (currentUser.tokens < stake) throw new Error("Not enough tokens.");

    const potential = stake * totalOdds;
    const record = {
      id: `bet_${Date.now()}`,
      stake,
      totalOdds,
      potential: Math.round(potential * 100) / 100,
      legs: slip.length,
      picks: slip.map((s) => ({ pick: s.pick, odds: s.odds, match: s.match })),
      placedAt: Date.now(),
      status: "open",
    };

    if (useFirebase()) await updateTokensFirebase(-stake, record);
    else await updateTokensLocal(-stake, record);
    return record;
  },

  formatSlipForShare(slip, stake, totalOdds) {
    const user = currentUser ? currentUser.username : "Guest";
    const lines = [
      `🧾 WC26 Bet Slip — ${user}`,
      "─".repeat(32),
      ...slip.map((s, i) => `${i + 1}. ${s.pick} @${s.odds.toFixed(2)}\n   ${s.match} · ${s.marketName}`),
      "─".repeat(32),
      `Legs: ${slip.length}`,
      `Combined odds: @${totalOdds >= 100 ? totalOdds.toFixed(0) : totalOdds.toFixed(2)}`,
      `Stake: ${stake} tokens`,
      `Potential return: ${(stake * totalOdds).toFixed(2)} tokens`,
      "",
      "Fair odds from Poisson model — for fun, not real betting.",
      "https://omeryaacobi.github.io/ML-WC26-Prediction/",
    ];
    return lines.join("\n");
  },
};
