# build_script.py
import os

html_code = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sign in \u2013 Google Accounts</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --g-blue: #1a73e8;
      --g-blue-hover: #1765cc;
      --g-gray-bg: #f8f9fa;
      --g-border: #dadce0;
      --g-text: #202124;
      --g-text-sub: #5f6368;
      --g-hover: #f1f3f4;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #ffffff;
      color: var(--g-text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
      -webkit-font-smoothing: antialiased;
    }

    .auth-container {
      width: 100%;
      max-width: 450px;
      border: 1px solid var(--g-border);
      border-radius: 8px;
      padding: 40px 36px 36px;
      background: #ffffff;
      position: relative;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(60,64,67,0.08), 0 4px 8px 3px rgba(60,64,67,0.04);
    }

    .google-progress {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
      background-color: #e8f0fe;
      overflow: hidden;
      display: none;
    }

    .google-progress.active { display: block; }

    .google-progress-bar {
      width: 100%;
      height: 100%;
      background-color: var(--g-blue);
      animation: googleIndeterminate 1.5s infinite linear;
      transform-origin: 0% 50%;
    }

    @keyframes googleIndeterminate {
      0% { transform: translateX(0) scaleX(0.05); }
      50% { transform: translateX(35%) scaleX(0.5); }
      100% { transform: translateX(100%) scaleX(0.1); }
    }

    .google-header {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      margin-bottom: 24px;
    }

    .google-logo {
      width: 75px;
      height: 24px;
      margin-bottom: 16px;
    }

    .google-heading {
      font-size: 24px;
      font-weight: 400;
      color: var(--g-text);
      line-height: 1.3333;
      margin-bottom: 8px;
    }

    .google-subheading {
      font-size: 16px;
      color: var(--g-text-sub);
      font-weight: 400;
    }

    .app-badge-box {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-top: 8px;
      padding: 5px 12px;
      background: #f1f3f4;
      border-radius: 16px;
      font-size: 13px;
      font-weight: 500;
      color: #3c4043;
    }

    .app-badge-box svg {
      width: 15px;
      height: 15px;
      fill: #1a73e8;
    }

    .accounts-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      border-top: 1px solid var(--g-border);
      border-bottom: 1px solid var(--g-border);
      margin-bottom: 24px;
    }

    .account-item {
      display: flex;
      align-items: center;
      padding: 14px 8px;
      cursor: pointer;
      transition: background 0.15s ease;
      position: relative;
    }

    .account-item:not(:last-child) {
      border-bottom: 1px solid rgba(218, 220, 224, 0.6);
    }

    .account-item:hover {
      background-color: var(--g-hover);
      border-radius: 4px;
    }

    .account-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: #4285F4;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 17px;
      font-weight: 500;
      margin-right: 16px;
      flex-shrink: 0;
    }

    .account-avatar.purple { background: #9334e6; }
    .account-avatar.gray {
      background: transparent;
      border: 1px solid var(--g-border);
      color: var(--g-text-sub);
    }

    .account-info {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
    }

    .account-name {
      font-size: 14px;
      font-weight: 500;
      color: var(--g-text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .account-email {
      font-size: 12px;
      color: var(--g-text-sub);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-top: 2px;
    }

    .account-chevron {
      color: var(--g-text-sub);
      margin-left: 8px;
    }

    #custom-account-pane {
      display: none;
      flex-direction: column;
      gap: 16px;
      margin-bottom: 24px;
    }

    .google-input-wrap {
      position: relative;
      margin-top: 6px;
    }

    .google-input {
      width: 100%;
      padding: 16px 14px;
      border: 1px solid var(--g-border);
      border-radius: 4px;
      font-size: 16px;
      outline: none;
      color: var(--g-text);
      background: transparent;
      transition: border 0.2s ease;
    }

    .google-input:focus {
      border: 2px solid var(--g-blue);
      padding: 15px 13px;
    }

    .google-floating-label {
      position: absolute;
      top: 50%;
      left: 14px;
      transform: translateY(-50%);
      font-size: 15px;
      color: var(--g-text-sub);
      pointer-events: none;
      transition: all 0.2s ease;
      background: #ffffff;
      padding: 0 4px;
    }

    .google-input:focus ~ .google-floating-label,
    .google-input:not(:placeholder-shown) ~ .google-floating-label {
      top: 0;
      font-size: 12px;
      color: var(--g-blue);
      font-weight: 500;
    }

    .btn-google-next {
      background-color: var(--g-blue);
      color: #ffffff;
      border: none;
      border-radius: 4px;
      padding: 10px 24px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      align-self: flex-end;
      transition: background 0.15s ease;
    }

    .btn-google-next:hover { background-color: var(--g-blue-hover); }

    .btn-google-back {
      background: transparent;
      border: none;
      color: var(--g-blue);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      align-self: flex-start;
      padding: 4px 0;
    }

    .google-disclaimer {
      font-size: 12px;
      line-height: 1.5;
      color: var(--g-text-sub);
      margin-bottom: 16px;
    }

    .google-disclaimer a { color: var(--g-blue); text-decoration: none; }
    .google-disclaimer a:hover { text-decoration: underline; }

    .sandbox-pill {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      font-size: 12px;
      color: #137333;
      background: #e6f4ea;
      padding: 6px 12px;
      border-radius: 16px;
      margin-bottom: 20px;
    }

    .google-footer {
      width: 100%;
      max-width: 450px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 18px;
      font-size: 12px;
      color: var(--g-text-sub);
      padding: 0 10px;
    }

    .google-footer-links { display: flex; gap: 18px; }
    .google-footer a { color: var(--g-text-sub); text-decoration: none; }
    .google-footer a:hover { color: var(--g-text); }

    .lang-selector {
      background: transparent;
      border: none;
      font-size: 12px;
      color: var(--g-text-sub);
      cursor: pointer;
    }

    #signing-in-overlay {
      display: none;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      padding: 40px 0;
      text-align: center;
    }

    .spinner {
      width: 36px;
      height: 36px;
      border: 3px solid #e8eaed;
      border-top-color: var(--g-blue);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <div class="auth-container" id="auth-container">
    <div class="google-progress" id="google-progress">
      <div class="google-progress-bar"></div>
    </div>

    <div class="google-header">
      <svg class="google-logo" viewBox="0 0 74 24">
        <path fill="#4285F4" d="M9.24 18.57c-2.45 0-4.52-.84-6.17-2.52S.6 12.2.6 9.47s.83-4.92 2.47-6.6S6.79.35 9.24.35c2.44 0 4.41.83 5.92 2.49l-1.99 2.05c-1.1-1.12-2.4-1.68-3.93-1.68-1.74 0-3.21.58-4.39 1.74-1.18 1.16-1.78 2.66-1.78 4.52s.6 3.36 1.78 4.52 2.65 1.74 4.39 1.74c1.68 0 3.06-.5 4.14-1.51.78-.73 1.29-1.68 1.52-2.85H9.24V8.53h8.33c.09.48.13.98.13 1.51 0 2.46-.77 4.51-2.31 6.13-1.54 1.63-3.59 2.4-6.15 2.4z"/>
        <path fill="#EA4335" d="M25.7 18.57c-2.22 0-4.08-.77-5.59-2.3-1.51-1.54-2.26-3.46-2.26-5.77s.75-4.23 2.26-5.77 3.37-2.31 5.59-2.31 4.08.77 5.59 2.31c1.51 1.54 2.26 3.46 2.26 5.77s-.75 4.23-2.26 5.77c-1.51 1.53-3.37 2.3-5.59 2.3zm0-2.67c1.35 0 2.48-.48 3.38-1.45.9-1.02 1.35-2.25 1.35-3.69s-.45-2.67-1.35-3.69c-.9-.97-2.03-1.45-3.38-1.45s-2.48.48-3.38 1.45c-.9 1.02-1.35 2.25-1.35 3.69s.45 2.67 1.35 3.69c.9.97 2.03 1.45 3.38 1.45z"/>
        <path fill="#FBBC05" d="M42.35 18.57c-2.22 0-4.08-.77-5.59-2.3-1.51-1.54-2.26-3.46-2.26-5.77s.75-4.23 2.26-5.77 3.37-2.31 5.59-2.31 4.08.77 5.59 2.31c1.51 1.54 2.26 3.46 2.26 5.77s-.75 4.23-2.26 5.77c-1.51 1.53-3.37 2.3-5.59 2.3zm0-2.67c1.35 0 2.48-.48 3.38-1.45.9-1.02 1.35-2.25 1.35-3.69s-.45-2.67-1.35-3.69c-.9-.97-2.03-1.45-3.38-1.45s-2.48.48-3.38 1.45c-.9 1.02-1.35 2.25-1.35 3.69s.45 2.67 1.35 3.69c.9.97 2.03 1.45 3.38 1.45z"/>
        <path fill="#4285F4" d="M58.74 18.57c-1.92 0-3.52-.64-4.81-1.91v1.54h-2.88V.74h2.88v6.78c1.29-1.27 2.89-1.91 4.81-1.91 1.99 0 3.7.77 5.12 2.31 1.43 1.54 2.14 3.47 2.14 5.77s-.71 4.23-2.14 5.77c-1.42 1.54-3.13 2.31-5.12 2.31zm-.24-2.67c1.35 0 2.48-.48 3.38-1.45.9-1.02 1.35-2.25 1.35-3.69s-.45-2.67-1.35-3.69c-.9-.97-2.03-1.45-3.38-1.45s-2.48.48-3.38 1.45c-.9 1.02-1.35 2.25-1.35 3.69s.45 2.67 1.35 3.69c.9.97 2.03 1.45 3.38 1.45z"/>
        <path fill="#34A853" d="M68.53.74h2.88v17.46h-2.88z"/>
        <path fill="#EA4335" d="M80.89 18.57c-2.19 0-4.01-.76-5.46-2.29-1.45-1.53-2.18-3.45-2.18-5.78s.72-4.24 2.15-5.78c1.43-1.54 3.2-2.31 5.31-2.31 2.19 0 3.96.73 5.32 2.18 1.36 1.45 2.04 3.37 2.04 5.75v.71H76.24c.09 1.25.54 2.26 1.36 3.03.82.77 1.83 1.15 3.03 1.15 1.63 0 2.94-.7 3.94-2.11l2.25 1.42c-.65 1.05-1.54 1.93-2.67 2.64-1.13.72-2.43 1.08-3.9 1.08zm-5.6-7.85h6.97c-.09-1.09-.5-1.98-1.24-2.66-.74-.68-1.68-1.02-2.82-1.02-1.03 0-1.92.33-2.66 1-.74.67-1.16 1.56-1.25 2.68z"/>
      </svg>
      <h1 class="google-heading" id="google-heading-text">Choose an account</h1>
      <p class="google-subheading">to continue to <strong style="color: var(--g-text);">DocuMind AI</strong></p>
      <div class="app-badge-box">
        <svg viewBox="0 0 24 24">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
        <span>DocuMind AI Document Studio</span>
      </div>
    </div>

    <div class="sandbox-pill">
      <span>Sign in with Google</span>
    </div>

    <div id="signing-in-overlay">
      <div class="spinner"></div>
      <p style="font-size: 15px; font-weight: 500; color: var(--g-text);" id="signing-in-msg">Signing in to DocuMind AI...</p>
      <p style="font-size: 13px; color: var(--g-text-sub);">Please wait while we establish your secure session.</p>
    </div>

    <div id="accounts-selection-pane">
      <ul class="accounts-list">
        <li class="account-item" onclick="selectAccount('Abhishek Sharma', 'abhishek.sharma.ai@gmail.com')">
          <div class="account-avatar">A</div>
          <div class="account-info">
            <div class="account-name">Abhishek Sharma</div>
            <div class="account-email">abhishek.sharma.ai@gmail.com</div>
          </div>
          <svg class="account-chevron" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
          </svg>
        </li>

        <li class="account-item" onclick="selectAccount('DocuMind Workspace Admin', 'workspace.admin@gmail.com')">
          <div class="account-avatar purple">D</div>
          <div class="account-info">
            <div class="account-name">DocuMind Workspace Admin</div>
            <div class="account-email">workspace.admin@gmail.com</div>
          </div>
          <svg class="account-chevron" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
          </svg>
        </li>

        <li class="account-item" id="btn-use-another-account" onclick="showCustomInput()">
          <div class="account-avatar gray">
            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/>
            </svg>
          </div>
          <div class="account-info">
            <div class="account-name" style="font-weight: 400;">Use another account</div>
          </div>
        </li>
      </ul>

      <p class="google-disclaimer">
        To continue, Google will share your name, email address, and profile picture with <strong>DocuMind AI</strong>. Before using this app, you can review DocuMind AI's <a href="#">privacy policy</a> and <a href="#">terms of service</a>.
      </p>
    </div>

    <div id="custom-account-pane">
      <button class="btn-google-back" onclick="showAccountsList()">\u2190 Back to account list</button>
      
      <div class="google-input-wrap">
        <input type="email" id="custom-google-email" class="google-input" placeholder=" " required />
        <label class="google-floating-label">Email or phone</label>
      </div>

      <div class="google-input-wrap" id="password-wrap" style="display: none;">
        <input type="password" id="custom-google-password" class="google-input" placeholder=" " />
        <label class="google-floating-label">Enter your password</label>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
        <a href="#" style="font-size: 13px; color: var(--g-blue); text-decoration: none;">Forgot email?</a>
        <button class="btn-google-next" id="btn-custom-next" onclick="handleCustomNext()">Next</button>
      </div>
    </div>
  </div>

  <footer class="google-footer">
    <div>
      <select class="lang-selector">
        <option>English (United States)</option>
        <option>English (United Kingdom)</option>
        <option>Espa\u00f1ol</option>
        <option>Fran\u00e7ais</option>
        <option>Deutsch</option>
      </select>
    </div>
    <div class="google-footer-links">
      <a href="https://support.google.com/accounts" target="_blank">Help</a>
      <a href="https://policies.google.com/privacy" target="_blank">Privacy</a>
      <a href="https://policies.google.com/terms" target="_blank">Terms</a>
    </div>
  </footer>

  <script>
    const accountsPane = document.getElementById('accounts-selection-pane');
    const customPane = document.getElementById('custom-account-pane');
    const signingInOverlay = document.getElementById('signing-in-overlay');
    const progressBar = document.getElementById('google-progress');
    const headingText = document.getElementById('google-heading-text');
    const customEmailInput = document.getElementById('custom-google-email');
    const customPassInput = document.getElementById('custom-google-password');
    const passWrap = document.getElementById('password-wrap');
    const btnNext = document.getElementById('btn-custom-next');

    let customStep = 1;

    function showCustomInput() {
      accountsPane.style.display = 'none';
      customPane.style.display = 'flex';
      headingText.textContent = 'Sign in';
      customEmailInput.focus();
    }

    function showAccountsList() {
      customPane.style.display = 'none';
      accountsPane.style.display = 'block';
      headingText.textContent = 'Choose an account';
      customStep = 1;
      passWrap.style.display = 'none';
      btnNext.textContent = 'Next';
    }

    function handleCustomNext() {
      const email = customEmailInput.value.trim();
      if (!email) {
        alert('Please enter your Google email address');
        customEmailInput.focus();
        return;
      }

      if (customStep === 1) {
        customStep = 2;
        passWrap.style.display = 'block';
        headingText.textContent = 'Welcome';
        btnNext.textContent = 'Sign In';
        customPassInput.focus();
      } else {
        const name = email.split('@')[0].replace(/[._]/g, ' ');
        const formattedName = name.charAt(0).toUpperCase() + name.slice(1);
        selectAccount(formattedName, email);
      }
    }

    function selectAccount(name, email) {
      progressBar.classList.add('active');
      accountsPane.style.display = 'none';
      customPane.style.display = 'none';
      signingInOverlay.style.display = 'flex';
      headingText.textContent = 'Connecting...';
      document.getElementById('signing-in-msg').textContent = 'Signing in as ' + name + '...';

      const userPayload = {
        name: name,
        email: email,
        provider: 'google',
        plan: 'Pro Tier',
        verified: true,
        authTime: Date.now()
      };

      setTimeout(() => {
        localStorage.setItem('documind_user_auth', JSON.stringify(userPayload));

        if (window.opener && !window.opener.closed) {
          try {
            window.opener.postMessage({
              type: 'GOOGLE_SIGNIN_SUCCESS',
              user: userPayload
            }, '*');
          } catch(e) {
            console.warn('PostMessage error:', e);
          }
          setTimeout(() => {
            window.close();
          }, 400);
        } else {
          window.location.href = '/#studio';
        }
      }, 700);
    }
  </script>
</body>
</html>
"""

with open('frontend/google-signin.html', 'w', encoding='utf-8') as f:
    f.write(html_code)
print('Successfully wrote frontend/google-signin.html')

