// Capture current webcam frame and send it to the agent as a progress photo
function sendProgressPhoto(websocket) {
    const video = document.getElementById('webcam');
    if (!video || !video.videoWidth) {
        console.warn('Camera not ready');
        return;
    }
    const canvas = document.createElement('canvas');
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    const base64Image = canvas.toDataURL('image/jpeg').split(',')[1];

    websocket.send(JSON.stringify({
        type: "image",
        mime_type: "image/jpeg",
        data: base64Image
    }));
}