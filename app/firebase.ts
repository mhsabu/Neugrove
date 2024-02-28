// For Firebase v9 and later
import { initializeApp } from 'firebase/app';
import { getDatabase } from 'firebase/database';
const firebaseConfig = {
    apiKey: "AIzaSyBAE1hv8hAZSiR1ux6wj4Fb3aiLz5l-m9s",
    authDomain: "https://grovechat-ca766-default-rtdb.firebaseio.com/",
    databaseURL: "https://grovechat-ca766-default-rtdb.firebaseio.com/",
    projectId: "grovechat-ca766",
    storageBucket: "grovechat-ca766.appspot.com",
    messagingSenderId: "106179324212",
    appId: "1:106179324212:web:38e4ae478881ccce09dd61",
    measurementId: "G-MW01L4MQBK"
  };
  
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

export default database;

