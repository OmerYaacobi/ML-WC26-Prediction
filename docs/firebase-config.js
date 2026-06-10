// Set enabled: true and paste your Firebase web app config to sync the league globally.
// Create a free project at https://console.firebase.google.com
// Enable Authentication (Email/Password) and Cloud Firestore.
// Firestore rules — paste in Firebase Console → Firestore → Rules → Publish:
//   rules_version = '2';
//   service cloud.firestore {
//     match /databases/{database}/documents {
//       match /users/{userId} {
//         allow read: if true;
//         allow create, update: if request.auth != null && request.auth.uid == userId;
//       }
//     }
//   }
const FIREBASE_CONFIG = {
  enabled: true,
  apiKey: "AIzaSyCk7ptnhEfg-lEfXlKHQ4enj5Gybk3nJ6I",
  authDomain: "ml-wc26-prediction.firebaseapp.com",
  projectId: "ml-wc26-prediction",
  storageBucket: "ml-wc26-prediction.firebasestorage.app",
  messagingSenderId: "223109549154",
  appId: "1:223109549154:web:d0d9934052ed09cb4d153b",
  measurementId: "G-5YD210ST7Q"
};
