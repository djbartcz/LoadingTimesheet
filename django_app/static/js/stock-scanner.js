(function () {
    'use strict';

    function getBarcodeFormats() {
        if (typeof Html5QrcodeSupportedFormats === 'undefined') {
            return undefined;
        }
        return [
            Html5QrcodeSupportedFormats.QR_CODE,
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.CODE_93,
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.ITF,
            Html5QrcodeSupportedFormats.DATA_MATRIX,
        ];
    }

    function initStockScanner() {
        const urls = window.STOCK_SCANNER_URLS;
        const startScreen = document.getElementById('startScreen');
        const scannerScreen = document.getElementById('scannerScreen');
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const retryBtn = document.getElementById('retryBtn');
        const cameraError = document.getElementById('cameraError');
        const cameraErrorText = document.getElementById('cameraErrorText');
        const cameraLoading = document.getElementById('cameraLoading');
        const statusText = document.getElementById('statusText');
        const confirmModal = document.getElementById('confirmModal');
        const modalBackdrop = document.getElementById('modalBackdrop');
        const scanFields = document.getElementById('scanFields');
        const cancelBtn = document.getElementById('cancelBtn');
        const saveBtn = document.getElementById('saveBtn');
        const scanHistory = document.getElementById('scanHistory');
        const emptyHistory = document.getElementById('emptyHistory');
        const toast = document.getElementById('toast');

        if (!urls || !startBtn || !statusText || !scannerScreen) {
            console.error('Stock scanner: missing required page elements or URLs');
            return;
        }

        let html5QrCode = null;
        let pendingBarcode = null;
        let modalOpen = false;
        let lastCode = '';
        let lastCodeTime = 0;
        let isStarting = false;
        const DEBOUNCE_MS = 2500;

        function getCsrfToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) return meta.getAttribute('content');
            const match = document.cookie.match(/csrftoken=([^;]+)/);
            return match ? decodeURIComponent(match[1]) : '';
        }

        function waitForNextPaint() {
            return new Promise(function (resolve) {
                requestAnimationFrame(function () {
                    requestAnimationFrame(resolve);
                });
            });
        }

        function showToast(message, isError) {
            if (!toast) return;
            toast.textContent = message;
            toast.className =
                'fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-lg shadow-lg text-sm font-medium text-white max-w-xs text-center ' +
                (isError ? 'bg-red-600' : 'bg-green-600');
            toast.classList.remove('hidden');
            setTimeout(function () {
                toast.classList.add('hidden');
            }, 3000);
        }

        function parseBarcode(raw) {
            const parts = raw.split(';').map(function (p) {
                return p.trim();
            });
            while (parts.length && parts[parts.length - 1] === '') {
                parts.pop();
            }
            if (parts.length === 6) {
                return {
                    part_no: parts[0],
                    part_description: parts[1],
                    lot_no: parts[2],
                    wdr: parts[3],
                    length: parts[4],
                    width: null,
                    handling_unit: parts[5],
                };
            }
            if (parts.length === 7) {
                return {
                    part_no: parts[0],
                    part_description: parts[1],
                    lot_no: parts[2],
                    wdr: parts[3],
                    length: parts[4],
                    width: parts[5],
                    handling_unit: parts[6],
                };
            }
            throw new Error('Expected 6 or 7 fields, got ' + parts.length);
        }

        function formatFieldLabel(key) {
            return key.replace(/_/g, ' ').replace(/\b\w/g, function (c) {
                return c.toUpperCase();
            });
        }

        function escapeHtml(value) {
            const div = document.createElement('div');
            div.textContent = value;
            return div.innerHTML;
        }

        function showConfirmModal(raw) {
            let fields;
            try {
                fields = parseBarcode(raw);
            } catch (err) {
                showToast(err.message, true);
                return;
            }

            pendingBarcode = raw;
            modalOpen = true;
            scanFields.innerHTML = Object.entries(fields)
                .filter(function (entry) {
                    return entry[1] !== null && entry[1] !== '';
                })
                .map(function (entry) {
                    return (
                        '<div class="flex justify-between gap-4 py-1 border-b border-gray-100">' +
                        '<dt class="text-gray-500">' + formatFieldLabel(entry[0]) + '</dt>' +
                        '<dd class="font-medium text-gray-900 text-right break-all">' +
                        escapeHtml(String(entry[1])) +
                        '</dd></div>'
                    );
                })
                .join('');
            confirmModal.classList.remove('hidden');
            statusText.textContent = 'Review scan';
        }

        function hideConfirmModal() {
            confirmModal.classList.add('hidden');
            pendingBarcode = null;
            modalOpen = false;
            if (scannerScreen.classList.contains('hidden')) {
                statusText.textContent = 'Ready to scan';
            } else {
                statusText.textContent = 'Scanning…';
            }
        }

        function renderHistory(scans) {
            scanHistory.querySelectorAll('.scan-item').forEach(function (el) {
                el.remove();
            });

            if (!scans.length) {
                emptyHistory.classList.remove('hidden');
                return;
            }

            emptyHistory.classList.add('hidden');
            scans.forEach(function (scan) {
                const item = document.createElement('div');
                item.className = 'scan-item bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm';
                const when = scan.scanned_at
                    ? new Date(scan.scanned_at).toLocaleString()
                    : '';
                item.innerHTML =
                    '<div class="font-semibold text-gray-900">' +
                    escapeHtml(scan.part_no || '') +
                    '</div>' +
                    '<div class="text-gray-600 text-xs mt-1">' +
                    escapeHtml(scan.part_description || '') +
                    '</div>' +
                    '<div class="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-xs text-gray-500">' +
                    '<span>Lot: ' + escapeHtml(scan.lot_no || '-') + '</span>' +
                    '<span>HU: ' + escapeHtml(scan.handling_unit || '-') + '</span>' +
                    '</div>' +
                    '<div class="text-xs text-gray-400 mt-1">' +
                    escapeHtml(when) +
                    '</div>';
                scanHistory.appendChild(item);
            });
        }

        async function loadRecent() {
            try {
                const response = await fetch(urls.recent);
                const data = await response.json();
                renderHistory(data.scans || []);
            } catch (err) {
                console.error(err);
            }
        }

        async function saveScan() {
            if (!pendingBarcode) return;

            saveBtn.disabled = true;
            try {
                const response = await fetch(urls.save, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                    },
                    body: JSON.stringify({ barcode: pendingBarcode }),
                });
                const data = await response.json();
                if (!response.ok || !data.success) {
                    throw new Error(data.message || 'Save failed');
                }
                showToast(data.message || 'Scan saved');
                hideConfirmModal();
                await loadRecent();
            } catch (err) {
                showToast(err.message || 'Save failed', true);
            } finally {
                saveBtn.disabled = false;
            }
        }

        function onScanSuccess(decodedText) {
            if (modalOpen) return;

            const now = Date.now();
            const trimmed = decodedText.trim();
            if (trimmed === lastCode && now - lastCodeTime < DEBOUNCE_MS) {
                return;
            }

            lastCode = trimmed;
            lastCodeTime = now;
            showConfirmModal(trimmed);
        }

        function ensureCameraSupport() {
            if (!window.isSecureContext) {
                throw new Error(
                    'Camera requires HTTPS or localhost. Open this page with https:// or http://localhost.'
                );
            }
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Camera is not supported in this browser.');
            }
        }

        async function requestCameraPermission() {
            ensureCameraSupport();

            const attempts = [
                { video: { facingMode: { ideal: 'environment' } }, audio: false },
                { video: { facingMode: 'user' }, audio: false },
                { video: true, audio: false },
            ];

            let lastError = null;
            for (let i = 0; i < attempts.length; i += 1) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia(attempts[i]);
                    stream.getTracks().forEach(function (track) {
                        track.stop();
                    });
                    return;
                } catch (err) {
                    lastError = err;
                }
            }

            throw lastError || new Error('Could not access camera');
        }

        async function resolveCameraId() {
            const cameras = await Html5Qrcode.getCameras();
            if (!cameras || !cameras.length) {
                throw new Error('No camera found on this device');
            }

            const preferred = cameras.find(function (camera) {
                return /back|rear|environment/i.test(camera.label || '');
            });
            return (preferred || cameras[0]).id;
        }

        function showCameraError(err) {
            cameraLoading.classList.add('hidden');
            scannerScreen.classList.add('hidden');
            startScreen.classList.remove('hidden');
            cameraError.classList.remove('hidden');

            let message = (err && err.message) ? err.message : 'Could not access camera';
            if (err && err.name === 'NotAllowedError') {
                message = 'Camera permission denied. Allow camera access for this site and try again.';
            } else if (err && err.name === 'NotFoundError') {
                message = 'No camera found on this device.';
            } else if (err && err.name === 'NotReadableError') {
                message = 'Camera is already in use by another application.';
            }

            cameraErrorText.textContent = message;
            statusText.textContent = 'Camera error';
            showToast(message, true);
        }

        async function startScanner() {
            if (isStarting) return;
            isStarting = true;
            startBtn.disabled = true;

            cameraError.classList.add('hidden');
            cameraLoading.classList.remove('hidden');
            startScreen.classList.add('hidden');
            scannerScreen.classList.remove('hidden');
            statusText.textContent = 'Requesting camera access…';

            try {
                if (typeof Html5Qrcode === 'undefined') {
                    throw new Error('Scanner library failed to load. Check your internet connection.');
                }

                await requestCameraPermission();
                await waitForNextPaint();

                const cameraId = await resolveCameraId();
                const formats = getBarcodeFormats();
                const scannerOptions = formats ? { formatsToSupport: formats, verbose: false } : undefined;
                html5QrCode = new Html5Qrcode('reader', scannerOptions);

                const config = {
                    fps: 10,
                    qrbox: function (viewfinderWidth, viewfinderHeight) {
                        const width = Math.min(viewfinderWidth * 0.9, 320);
                        const height = Math.min(viewfinderHeight * 0.45, 180);
                        return { width: Math.floor(width), height: Math.floor(height) };
                    },
                    aspectRatio: 1.777778,
                    disableFlip: false,
                };

                await html5QrCode.start(
                    cameraId,
                    config,
                    onScanSuccess,
                    function () {}
                );

                cameraLoading.classList.add('hidden');
                statusText.textContent = 'Scanning…';
                await loadRecent();
            } catch (err) {
                console.error('Camera start failed:', err);
                if (html5QrCode) {
                    try {
                        await html5QrCode.stop();
                        html5QrCode.clear();
                    } catch (stopErr) {
                        // ignore
                    }
                    html5QrCode = null;
                }
                showCameraError(err);
            } finally {
                isStarting = false;
                startBtn.disabled = false;
            }
        }

        async function stopScanner() {
            if (html5QrCode) {
                try {
                    await html5QrCode.stop();
                    html5QrCode.clear();
                } catch (err) {
                    // ignore stop errors
                }
                html5QrCode = null;
            }
            hideConfirmModal();
            scannerScreen.classList.add('hidden');
            startScreen.classList.remove('hidden');
            statusText.textContent = 'Ready to scan';
        }

        startBtn.addEventListener('click', function (event) {
            event.preventDefault();
            startScanner();
        });
        stopBtn.addEventListener('click', stopScanner);
        retryBtn.addEventListener('click', function () {
            cameraError.classList.add('hidden');
            startScanner();
        });
        cancelBtn.addEventListener('click', hideConfirmModal);
        modalBackdrop.addEventListener('click', hideConfirmModal);
        saveBtn.addEventListener('click', saveScan);

        statusText.textContent = 'Ready to scan';
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStockScanner);
    } else {
        initStockScanner();
    }
})();
