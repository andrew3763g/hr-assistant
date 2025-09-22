(async () => {
  const video = document.getElementById("preview");
  window.__mediaStream = await navigator.mediaDevices.getUserMedia({
    video: true,
    audio: true,
  });
  video.srcObject = window.__mediaStream;
})();
