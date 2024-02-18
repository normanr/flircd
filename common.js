if ('serviceWorker' in navigator) {
  // Register a service worker hosted at the root of the
  // site using the default scope.
  if(0) {
  navigator.serviceWorker.register('worker.js').then(function(registration) {
    console.log('Service worker registration succeeded: ' + (registration.waiting ? "waiting to update..." : "no update"));
  }, /*catch*/ function(error) {
    console.error('Service worker registration failed:', error);
  });
  }
} else {
  console.warn('Service workers are not supported.');
}

let touchstart = async (event) => {
  let button = event.target.closest('button');
  if (!button) return;
  event.preventDefault();
  console.log(event.type, button.dataset.keycode)
  let data = {
    "keymap": button.closest('device').dataset.keymap,
    "keycode": button.dataset.keycode,
  };
  let led = document.getElementById('led');
  led.style = "color:red";
  let query = Object.entries(data).map(([k, v]) => escape(k) + '=' + escape(v)).join('&');
  const request = new Request("/cgi-bin/ir-ctl-send?" + query, {
    method: 'POST',
    headers: {
      'Accept': 'text/plain',
    },
  })
  let response;
  try {
    response = await fetch(request);
  } catch (err) {
    led.style = "";
    alert("Error trying to connect to server: " + err);
    return;
  }
  if (response.status == 401 /* Unauthorized */) {
    data.redirect = location.pathname;
    let query = Object.entries(data).map(([k, v]) => escape(k) + '=' + escape(v)).join('&');
    const f = document.createElement('form');
    f.style.display = 'none';
    f.method = 'POST';
    f.action = "/cgi-bin/ir-ctl-send?" + query;
    document.body.appendChild(f);
    f.submit();
    return;
  }
  led.style = "";
  response_text = await response.text();
  msg = response.status + " " + response.statusText + ":\n" + response_text;
  if (response.status >= 200 && response.status < 300) {
    if (response.status > 200 && response_text) {
      console.warn("POST " + response.url + " " + msg);
      alert(msg);
    }
  } else {
    alert(msg);
  }
};
let touchend = (event) => {
  let button = event.target.closest('button');
  if (!button) return;
  event.preventDefault();
  console.log(event.type, button.dataset.keycode)
};
let buttondown = (event) => {
  if (event.button == 0) touchstart(event)
}
let buttonup = (event) => {
  if (event.button == 0) touchend(event)
}
[...document.getElementsByTagName('device')].forEach(element => {
  element.addEventListener('touchstart', touchstart);
  element.addEventListener('mousedown', buttondown);
  element.addEventListener('touchend', touchend);
  element.addEventListener('mouseup', buttonup);
});
