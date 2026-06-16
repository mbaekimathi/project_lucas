(function () {
    if (window._studentFingerprintEnrollmentRegistered) return;

    const FINGERPRINT_SERVICE = 'http://127.0.0.1:9765';
    const FINGER_OPTIONS = [
        { code: 'right_thumb', label: 'Right thumb', hand: 'right', short: 'R · Thumb' },
        { code: 'right_index', label: 'Right index', hand: 'right', short: 'R · Index' },
        { code: 'right_middle', label: 'Right middle', hand: 'right', short: 'R · Middle' },
        { code: 'right_ring', label: 'Right ring', hand: 'right', short: 'R · Ring' },
        { code: 'right_little', label: 'Right little', hand: 'right', short: 'R · Little' },
        { code: 'left_thumb', label: 'Left thumb', hand: 'left', short: 'L · Thumb' },
        { code: 'left_index', label: 'Left index', hand: 'left', short: 'L · Index' },
        { code: 'left_middle', label: 'Left middle', hand: 'left', short: 'L · Middle' },
        { code: 'left_ring', label: 'Left ring', hand: 'left', short: 'L · Ring' },
        { code: 'left_little', label: 'Left little', hand: 'left', short: 'L · Little' },
    ];

    const WIZARD_STEPS = [
        { id: 'scan', label: 'Place finger' },
        { id: 'register', label: 'Register' },
        { id: 'done', label: 'Done' },
    ];

    function registerStudentFingerprintEnrollment() {
        if (window._studentFingerprintEnrollmentRegistered) return;
        window._studentFingerprintEnrollmentRegistered = true;

        Alpine.data('studentFingerprintEnrollment', (cfg) => ({
            mode: cfg.mode || 'live',
            studentId: cfg.studentId || '',
            hiddenInputId: cfg.hiddenInputId || 'admission_fingerprints_json',
            apiPrefix: cfg.apiPrefix || '',
            fingerOptions: FINGER_OPTIONS,
            wizardSteps: WIZARD_STEPS,
            fingerCode: '',
            enrollments: [],
            capturing: false,
            captureError: '',
            captureMessage: '',
            scannerReady: false,
            wizardOpen: false,
            wizardStep: 'scanning',
            lastQuality: null,
            captureAbort: null,

            fingerLabel(code) {
                const f = FINGER_OPTIONS.find((o) => o.code === code);
                return f ? f.label : code;
            },

            fingerMeta(code) {
                return FINGER_OPTIONS.find((o) => o.code === code) || null;
            },

            isFingerHighlighted(code) {
                return this.fingerCode === code;
            },

            wizardStepIndex() {
                if (this.wizardStep === 'scanning') return 0;
                if (this.wizardStep === 'success' || this.wizardStep === 'error') return 2;
                return 0;
            },

            async init() {
                await this.checkScanner();
                if (this.mode === 'live' && this.studentId) {
                    await this.loadEnrollments();
                }
                if (!this._fpReloadBound) {
                    this._fpReloadBound = true;
                    window.addEventListener('student-fingerprint-reload', (e) => {
                        if (!e.detail || !e.detail.studentId) return;
                        if (this.mode !== 'live') return;
                        this.studentId = e.detail.studentId;
                        this.loadEnrollments();
                    });
                }
            },

            async onFingerSelected() {
                if (!this.fingerCode) {
                    this.closeWizard(false);
                    return;
                }
                this.captureError = '';
                this.captureMessage = '';
                this.lastQuality = null;
                this.wizardOpen = true;
                await this.checkScanner();
                await this.$nextTick();
                await this.startWizardScan();
            },

            closeWizard(clearFinger) {
                if (this.captureAbort) {
                    this.captureAbort.abort();
                    this.captureAbort = null;
                }
                this.wizardOpen = false;
                this.wizardStep = 'scanning';
                this.capturing = false;
                if (clearFinger) {
                    this.fingerCode = '';
                }
            },

            async startWizardScan() {
                if (!this.fingerCode) return;
                if (this.capturing && this.captureAbort) {
                    this.captureAbort.abort();
                    this.captureAbort = null;
                }
                this.captureError = '';
                this.wizardStep = 'scanning';
                await this.captureFingerprint(true);
            },

            async retryWizardScan() {
                this.captureError = '';
                this.wizardStep = 'scanning';
                await this.captureFingerprint(true);
            },

            registerAnotherFinger() {
                this.closeWizard(true);
            },

            async checkScanner() {
                try {
                    const res = await fetch(FINGERPRINT_SERVICE + '/api/health', { method: 'GET' });
                    const data = await res.json();
                    this.scannerReady = !!(data && data.ok && data.ready);
                } catch (e) {
                    this.scannerReady = false;
                }
            },

            async loadEnrollments() {
                if (!this.studentId || !this.apiPrefix) return;
                try {
                    const res = await fetch(
                        this.apiPrefix + '/student-management/fingerprints/' + encodeURIComponent(this.studentId),
                        { credentials: 'same-origin', headers: { Accept: 'application/json' } }
                    );
                    const data = await res.json();
                    if (data.success) {
                        this.enrollments = (data.fingerprints || []).map((row) => ({
                            key: 'db-' + row.id,
                            id: row.id,
                            finger_code: row.finger_code,
                            finger_label: row.finger_label,
                            quality_score: row.quality_score,
                        }));
                    }
                } catch (e) {
                    console.error(e);
                }
            },

            queuedJson() {
                const queued = this.enrollments.filter((x) => x.template_base64).map((x) => ({
                    finger_code: x.finger_code,
                    template_base64: x.template_base64,
                    template_format: x.template_format || 'binary_v1',
                    quality_score: x.quality_score,
                    device_id: x.device_id,
                }));
                return JSON.stringify(queued);
            },

            async captureFingerprint(fromWizard) {
                if (!fromWizard) {
                    if (!this.fingerCode) {
                        this.captureError = 'Select which finger to register.';
                        return;
                    }
                    this.wizardOpen = true;
                    this.wizardStep = 'scanning';
                }

                this.captureError = '';
                this.captureMessage = '';
                if (!this.fingerCode) {
                    this.captureError = 'Select which finger to register.';
                    this.wizardStep = 'error';
                    return;
                }

                this.capturing = true;
                const controller = new AbortController();
                this.captureAbort = controller;
                try {
                    await this.checkScanner();
                    const res = await fetch(FINGERPRINT_SERVICE + '/api/capture', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: '{}',
                        signal: controller.signal,
                    });
                    const data = await res.json();
                    if (!res.ok || !data.success || !data.template_base64) {
                        this.captureError = (data && data.message) || 'Capture failed. Start fingerprint_local_service.py on this PC.';
                        this.wizardStep = 'error';
                        return;
                    }

                    if (this.mode === 'live') {
                        if (!this.studentId) {
                            this.captureError = 'Student record not loaded. Close and open Edit again.';
                            this.wizardStep = 'error';
                            return;
                        }
                        const saveRes = await fetch(
                            this.apiPrefix + '/student-management/fingerprints/' + encodeURIComponent(this.studentId),
                            {
                                method: 'POST',
                                credentials: 'same-origin',
                                headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
                                body: JSON.stringify({
                                    finger_code: this.fingerCode,
                                    template_base64: data.template_base64,
                                    template_format: data.template_format || 'binary_v1',
                                    quality_score: data.quality_score,
                                    device_id: data.device_id,
                                }),
                            }
                        );
                        const saveData = await saveRes.json();
                        if (!saveRes.ok || !saveData.success) {
                            this.captureError = saveData.message || 'Could not save fingerprint.';
                            this.wizardStep = 'error';
                            return;
                        }
                        this.captureMessage = saveData.message || 'Fingerprint saved successfully.';
                        await this.loadEnrollments();
                    } else {
                        const key = 'q-' + this.fingerCode;
                        this.enrollments = this.enrollments.filter((x) => x.finger_code !== this.fingerCode);
                        this.enrollments.push({
                            key,
                            finger_code: this.fingerCode,
                            finger_label: this.fingerLabel(this.fingerCode),
                            template_base64: data.template_base64,
                            template_format: data.template_format || 'binary_v1',
                            quality_score: data.quality_score,
                            device_id: data.device_id,
                            simulated: !!data.simulated,
                        });
                        this.captureMessage = 'Fingerprint queued — submit the form to save with the student.';
                    }

                    this.lastQuality = data.quality_score != null ? data.quality_score : null;
                    this.wizardStep = 'success';
                } catch (e) {
                    if (e && e.name === 'AbortError') {
                        return;
                    }
                    console.error(e);
                    this.captureError = 'Could not reach the fingerprint scanner on this computer.';
                    this.wizardStep = 'error';
                } finally {
                    this.capturing = false;
                    this.captureAbort = null;
                }
            },

            async removeEnrollment(item) {
                if (!confirm('Remove this fingerprint enrollment?')) return;
                if (this.mode === 'live' && item.id) {
                    try {
                        const res = await fetch(
                            this.apiPrefix + '/student-management/fingerprints/' + encodeURIComponent(this.studentId) + '/' + item.id,
                            { method: 'DELETE', credentials: 'same-origin', headers: { Accept: 'application/json' } }
                        );
                        const data = await res.json();
                        if (!res.ok || !data.success) {
                            alert(data.message || 'Could not remove fingerprint.');
                            return;
                        }
                        await this.loadEnrollments();
                    } catch (e) {
                        alert('Could not remove fingerprint.');
                    }
                } else {
                    this.enrollments = this.enrollments.filter((x) => x.key !== item.key);
                }
            },
        }));
    }

    if (typeof Alpine !== 'undefined') {
        registerStudentFingerprintEnrollment();
    } else {
        document.addEventListener('alpine:init', registerStudentFingerprintEnrollment);
    }
})();
