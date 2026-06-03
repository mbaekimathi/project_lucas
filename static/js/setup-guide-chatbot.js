/**
 * Floating setup guide chatbot for role-based onboarding
 * (curriculum coordinator, accountant / finance).
 * Detects current page and shows contextual on-page guidance.
 */
(function () {
    'use strict';

    var REACTIONS = ['👍', '✅', '🎉', '💡', '🙌'];
    var TYPING_MS = 650;
    var MSG_DELAY_MS = 420;
    var STORAGE_AUTO_OPEN = 'sgc_auto_open';
    var STORAGE_CHECKLIST = 'sgc_checklist_';

    function el(tag, className, html) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (html != null) node.innerHTML = html;
        return node;
    }

    function scrollMessages(container) {
        requestAnimationFrame(function () {
            container.scrollTop = container.scrollHeight;
        });
    }

    function wait(ms) {
        return new Promise(function (resolve) {
            setTimeout(resolve, ms);
        });
    }

    function normalizePath(path) {
        return String(path || '')
            .toLowerCase()
            .replace(/\/+$/, '') || '/';
    }

    function pathMatches(path, key) {
        var p = normalizePath(path);
        var k = String(key || '').toLowerCase().replace(/^\//, '');
        if (!k) return false;
        var segment = '/' + k;
        if (p === segment || p.endsWith(segment)) return true;
        return p.indexOf(segment + '/') !== -1;
    }

    function longestPathKey(guide) {
        var keys = guide.pathKeys || [];
        var best = 0;
        for (var i = 0; i < keys.length; i++) {
            var len = String(keys[i] || '').length;
            if (len > best) best = len;
        }
        return best;
    }

    function SetupGuideChatbot(root, config) {
        this.root = root;
        this.config = config || {};
        this.steps = this.config.steps || [];
        this.pageGuides = this.config.pageGuides || [];
        this.currentStep = 0;
        this.open = false;
        this.busy = false;
        this.activePageGuide = null;
        this.currentPath = normalizePath(this.config.currentPath || window.location.pathname);

        this.fab = root.querySelector('[data-sgc-fab]');
        this.panel = root.querySelector('[data-sgc-panel]');
        this.messagesEl = root.querySelector('[data-sgc-messages]');
        this.chipsEl = root.querySelector('[data-sgc-chips]');
        this.prevBtn = root.querySelector('[data-sgc-prev]');
        this.nextBtn = root.querySelector('[data-sgc-next]');
        this.restartBtn = root.querySelector('[data-sgc-restart]');
        this.ctaWrap = root.querySelector('[data-sgc-cta-wrap]');
        this.ctaLinks = root.querySelector('[data-sgc-cta-links]');
        this.ctaLabel = root.querySelector('[data-sgc-cta-label]');
        this.titleEl = root.querySelector('[data-sgc-title]');
        this.subtitleEl = root.querySelector('[data-sgc-subtitle]');
        this.liveLabel = root.querySelector('[data-sgc-live-label]');
        this.roleLabel = this.config.roleLabel || 'Setup guide';
        this.assistantTitle = this.config.assistantTitle || 'Setup Assistant';
        this.pageHelpBtn = root.querySelector('[data-sgc-page-help]');
        this.progressWrap = root.querySelector('[data-sgc-progress]');
        this.progressFill = root.querySelector('[data-sgc-progress-fill]');
        this.progressText = root.querySelector('[data-sgc-progress-text]');
        this.resetChecklistBtn = root.querySelector('[data-sgc-reset-checklist]');
        this.activeChecklistId = null;

        this.activePageGuide = this.findPageGuideForPath(this.currentPath);
        if (this.activePageGuide != null && typeof this.activePageGuide.stepIndex === 'number') {
            this.currentStep = this.activePageGuide.stepIndex;
        }

        if (this.titleEl) this.titleEl.textContent = this.assistantTitle;

        this.bindEvents();
        this.renderChips();
        this.updateHeaderForPage();
        this.updateFabHint();

        if (this.activePageGuide && this.isOnActiveGuidePage()) {
            this.root.classList.add('is-on-page');
        }

        if (this.activePageGuide && sessionStorage.getItem(STORAGE_AUTO_OPEN) === '1') {
            sessionStorage.removeItem(STORAGE_AUTO_OPEN);
            this.openPanel(false);
        }
    }

    SetupGuideChatbot.prototype.findPageGuideForPath = function (path) {
        var guides = this.pageGuides.slice().sort(function (a, b) {
            return longestPathKey(b) - longestPathKey(a);
        });
        for (var i = 0; i < guides.length; i++) {
            var g = guides[i];
            var keys = (g.pathKeys || []).slice().sort(function (a, b) {
                return String(b || '').length - String(a || '').length;
            });
            for (var j = 0; j < keys.length; j++) {
                if (pathMatches(path, keys[j])) {
                    return g;
                }
            }
        }
        return null;
    };

    SetupGuideChatbot.prototype.updateHeaderForPage = function () {
        if (!this.subtitleEl) return;
        if (this.activePageGuide && this.activePageGuide.pageTitle) {
            this.subtitleEl.textContent = 'Helping on: ' + this.activePageGuide.pageTitle;
            if (this.liveLabel) this.liveLabel.textContent = 'On this page';
        } else {
            this.subtitleEl.textContent = this.roleLabel;
            if (this.liveLabel) this.liveLabel.textContent = 'Live guide';
        }
    };

    SetupGuideChatbot.prototype.updateFabHint = function () {
        if (!this.fab) return;
        if (this.activePageGuide && this.activePageGuide.pageTitle) {
            this.fab.title = 'Help for ' + this.activePageGuide.pageTitle;
        } else {
            this.fab.title = 'Open setup guide';
        }
    };

    SetupGuideChatbot.prototype.getStepLinks = function (step) {
        if (!step) return [];
        if (Array.isArray(step.links) && step.links.length) {
            return step.links.filter(function (l) {
                return l && l.href;
            });
        }
        if (step.link) {
            return [{ href: step.link, label: step.linkLabel || 'Open page' }];
        }
        return [];
    };

    SetupGuideChatbot.prototype.buildLinkButton = function (item, extraClass) {
        var self = this;
        var link = el('a', 'setup-guide-chatbot__link' + (extraClass ? ' ' + extraClass : ''));
        link.href = item.href;
        link.target = '_self';
        link.innerHTML =
            '<i class="fas fa-external-link-alt" aria-hidden="true"></i> ' +
            '<span>' + escapeHtml(item.label || 'Open page') + '</span>';
        link.addEventListener('click', function () {
            sessionStorage.setItem(STORAGE_AUTO_OPEN, '1');
        });
        return link;
    };

    SetupGuideChatbot.prototype.appendStepLinks = function (step, container) {
        var links = this.getStepLinks(step);
        if (!links.length) return;
        var wrap = el('div', 'setup-guide-chatbot__links');
        links.forEach(function (item) {
            wrap.appendChild(this.buildLinkButton(item, 'setup-guide-chatbot__link--action'));
        }.bind(this));
        container.appendChild(wrap);
    };

    SetupGuideChatbot.prototype.updateFooterLinks = function () {
        var step = this.steps[this.currentStep];
        var links = this.getStepLinks(step);
        if (!this.ctaWrap || !this.ctaLinks) return;

        var onMatchedPage = this.activePageGuide && this.isOnActiveGuidePage();

        this.ctaLinks.innerHTML = '';
        if (onMatchedPage) {
            this.ctaWrap.hidden = true;
            if (this.ctaLabel) this.ctaLabel.textContent = 'On this page';
            return;
        }

        if (!links.length) {
            this.ctaWrap.hidden = true;
            return;
        }

        this.ctaWrap.hidden = false;
        if (this.ctaLabel) this.ctaLabel.textContent = 'Go to this step';
        links.forEach(function (item) {
            this.ctaLinks.appendChild(this.buildLinkButton(item, 'setup-guide-chatbot__link--cta'));
        }.bind(this));
    };

    SetupGuideChatbot.prototype.isOnActiveGuidePage = function () {
        if (!this.activePageGuide) return false;
        var keys = this.activePageGuide.pathKeys || [];
        for (var i = 0; i < keys.length; i++) {
            if (pathMatches(this.currentPath, keys[i])) return true;
        }
        return false;
    };

    SetupGuideChatbot.prototype.bindEvents = function () {
        var self = this;
        this.fab.addEventListener('click', function () {
            self.toggle();
        });
        this.prevBtn.addEventListener('click', function () {
            if (!self.busy && self.currentStep > 0) self.showStep(self.currentStep - 1, true);
        });
        this.nextBtn.addEventListener('click', function () {
            if (self.busy) return;
            if (self.currentStep < self.steps.length - 1) {
                self.showStep(self.currentStep + 1, true);
            } else {
                self.finishGuide();
            }
        });
        if (this.restartBtn) {
            this.restartBtn.addEventListener('click', function () {
                if (!self.busy) self.startGuide(true);
            });
        }
        if (this.pageHelpBtn) {
            this.pageHelpBtn.addEventListener('click', function () {
                if (!self.busy && self.activePageGuide) {
                    self.clearMessages();
                    self.showPageGuide(self.activePageGuide, false);
                }
            });
        }
        if (this.resetChecklistBtn) {
            this.resetChecklistBtn.addEventListener('click', function () {
                if (!self.activeChecklistId) return;
                self.saveChecklistState(self.activeChecklistId, {});
                self.refreshActiveChecklistUi();
                self.renderChips();
            });
        }
    };

    SetupGuideChatbot.prototype.normalizeChecklist = function (source) {
        if (!source) return [];
        if (Array.isArray(source.checklist) && source.checklist.length) {
            return source.checklist.map(function (item, idx) {
                if (typeof item === 'string') {
                    return { id: 'item-' + idx, label: item };
                }
                return {
                    id: item.id || 'item-' + idx,
                    label: item.label || item.text || ''
                };
            }).filter(function (item) {
                return item.label;
            });
        }
        if (Array.isArray(source.tips) && source.tips.length) {
            return source.tips.map(function (tip, idx) {
                return { id: 'tip-' + idx, label: tip };
            });
        }
        return [];
    };

    SetupGuideChatbot.prototype.resolveChecklistId = function (source, fallback) {
        if (source && source.checklistId) return source.checklistId;
        if (source && source.id != null) return 'step-' + source.id;
        return fallback || 'checklist-default';
    };

    SetupGuideChatbot.prototype.loadChecklistState = function (checklistId) {
        try {
            var raw = localStorage.getItem(STORAGE_CHECKLIST + checklistId);
            if (!raw) return {};
            var parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (e) {
            return {};
        }
    };

    SetupGuideChatbot.prototype.saveChecklistState = function (checklistId, state) {
        try {
            localStorage.setItem(STORAGE_CHECKLIST + checklistId, JSON.stringify(state || {}));
        } catch (e) {
            /* ignore quota */
        }
    };

    SetupGuideChatbot.prototype.getChecklistProgress = function (checklistId, items) {
        var state = this.loadChecklistState(checklistId);
        var total = items.length;
        var done = 0;
        items.forEach(function (item) {
            if (state[item.id]) done += 1;
        });
        return { done: done, total: total, state: state };
    };

    SetupGuideChatbot.prototype.isChecklistComplete = function (checklistId, items) {
        var p = this.getChecklistProgress(checklistId, items);
        return p.total > 0 && p.done === p.total;
    };

    SetupGuideChatbot.prototype.updateProgressBar = function (checklistId, items) {
        if (!this.progressWrap) return;
        if (!items || !items.length) {
            this.progressWrap.hidden = true;
            return;
        }
        this.progressWrap.hidden = false;
        this.activeChecklistId = checklistId;
        var progress = this.getChecklistProgress(checklistId, items);
        var pct = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;
        if (this.progressFill) this.progressFill.style.width = pct + '%';
        if (this.progressText) {
            this.progressText.textContent =
                progress.done + ' of ' + progress.total + ' done' +
                (progress.done === progress.total && progress.total ? ' — complete!' : '');
        }
        if (this.resetChecklistBtn) {
            this.resetChecklistBtn.hidden = progress.done === 0;
        }
    };

    SetupGuideChatbot.prototype.appendChecklist = function (bubble, checklistId, items) {
        var self = this;
        if (!items || !items.length) return null;

        var state = this.loadChecklistState(checklistId);
        var heading = el('p', 'setup-guide-chatbot__tips-heading');
        heading.innerHTML = '<i class="fas fa-list-check"></i> Check off as you complete:';

        var list = el('ul', 'setup-guide-chatbot__checklist');
        list.setAttribute('data-sgc-checklist-id', checklistId);

        items.forEach(function (item) {
            var li = el('li', 'setup-guide-chatbot__check-item');
            var label = el('label', 'setup-guide-chatbot__check-label');

            var input = document.createElement('input');
            input.type = 'checkbox';
            input.className = 'setup-guide-chatbot__check-input';
            input.value = item.id;
            input.checked = !!state[item.id];
            if (state[item.id]) li.classList.add('is-done');

            var text = el('span', 'setup-guide-chatbot__check-text', escapeHtml(item.label));
            label.appendChild(input);
            label.appendChild(text);
            li.appendChild(label);
            list.appendChild(li);

            input.addEventListener('change', function () {
                var current = self.loadChecklistState(checklistId);
                current[item.id] = input.checked;
                if (!input.checked) delete current[item.id];
                self.saveChecklistState(checklistId, current);
                li.classList.toggle('is-done', input.checked);
                self.updateProgressBar(checklistId, items);
                self.renderChips();

                if (self.isChecklistComplete(checklistId, items)) {
                    self.flashBotReply('All items checked — great work! Use Next step when you are ready.');
                }
            });
        });

        bubble.appendChild(heading);
        bubble.appendChild(list);
        this.updateProgressBar(checklistId, items);
        return list;
    };

    SetupGuideChatbot.prototype.refreshActiveChecklistUi = function () {
        var list = this.messagesEl.querySelector('[data-sgc-checklist-id]');
        if (!list) return;
        var checklistId = list.getAttribute('data-sgc-checklist-id');
        var state = this.loadChecklistState(checklistId);
        list.querySelectorAll('.setup-guide-chatbot__check-item').forEach(function (li) {
            var input = li.querySelector('input');
            if (!input) return;
            input.checked = !!state[input.value];
            li.classList.toggle('is-done', input.checked);
        });
        var items = [];
        list.querySelectorAll('.setup-guide-chatbot__check-text').forEach(function (span, idx) {
            var input = list.querySelectorAll('input')[idx];
            items.push({ id: input ? input.value : 'item-' + idx, label: span.textContent });
        });
        this.updateProgressBar(checklistId, items);
    };

    SetupGuideChatbot.prototype.openPanel = function () {
        this.open = true;
        this.root.classList.add('is-open');
        this.fab.setAttribute('aria-expanded', 'true');
        if (this.messagesEl.childElementCount === 0) {
            this.openWithContext();
        }
    };

    SetupGuideChatbot.prototype.toggle = function () {
        if (this.open) {
            this.open = false;
            this.root.classList.remove('is-open');
            this.fab.setAttribute('aria-expanded', 'false');
            return;
        }
        this.openPanel(false);
    };

    SetupGuideChatbot.prototype.openWithContext = function () {
        if (this.activePageGuide && this.isOnActiveGuidePage()) {
            this.showPageGuide(this.activePageGuide, false);
        } else {
            this.startGuide(false);
        }
    };

    SetupGuideChatbot.prototype.setBusy = function (on) {
        this.busy = on;
        this.updateNav();
        if (this.restartBtn) this.restartBtn.disabled = on;
        if (this.pageHelpBtn) this.pageHelpBtn.disabled = on;
    };

    SetupGuideChatbot.prototype.clearMessages = function () {
        this.messagesEl.innerHTML = '';
    };

    SetupGuideChatbot.prototype.showTyping = function () {
        var wrap = el('div', 'setup-guide-chatbot__typing');
        wrap.setAttribute('data-sgc-typing', '1');
        wrap.setAttribute('aria-hidden', 'true');
        wrap.appendChild(el('span'));
        wrap.appendChild(el('span'));
        wrap.appendChild(el('span'));
        this.messagesEl.appendChild(wrap);
        scrollMessages(this.messagesEl);
        return wrap;
    };

    SetupGuideChatbot.prototype.removeTyping = function () {
        var t = this.messagesEl.querySelector('[data-sgc-typing]');
        if (t) t.remove();
    };

    SetupGuideChatbot.prototype.addUserMessage = function (text) {
        var msg = el('div', 'setup-guide-chatbot__msg setup-guide-chatbot__msg--user');
        msg.appendChild(el('div', 'setup-guide-chatbot__bubble', escapeHtml(text)));
        this.messagesEl.appendChild(msg);
        scrollMessages(this.messagesEl);
    };

    SetupGuideChatbot.prototype.addBotMessage = function (step, opts) {
        opts = opts || {};
        var msg = el('div', 'setup-guide-chatbot__msg setup-guide-chatbot__msg--bot');
        var bubble = el('div', 'setup-guide-chatbot__bubble');

        var displayTitle = step.pageTitle || step.title;
        if (displayTitle) {
            var titleEl = document.createElement('strong');
            titleEl.textContent = displayTitle;
            bubble.appendChild(titleEl);
            bubble.appendChild(document.createElement('br'));
        }
        if (step.message) {
            var msgP = document.createElement('span');
            msgP.textContent = step.message;
            bubble.appendChild(msgP);
        }

        var checklist = this.normalizeChecklist(step);
        var checklistId =
            opts.checklistId ||
            step.checklistId ||
            this.resolveChecklistId(step, 'checklist-' + (opts.stepIndex != null ? opts.stepIndex : this.currentStep));
        if (checklist.length) {
            this.appendChecklist(bubble, checklistId, checklist);
        }

        msg.appendChild(bubble);

        if (!opts.hideLinks) {
            this.appendStepLinks(step, msg);
        }

        this.appendReactions(msg, opts);
        this.messagesEl.appendChild(msg);
        scrollMessages(this.messagesEl);
    };

    SetupGuideChatbot.prototype.appendReactions = function (msg, opts) {
        opts = opts || {};
        var reactions = el('div', 'setup-guide-chatbot__reactions');
        var self = this;
        REACTIONS.forEach(function (emoji) {
            var btn = el('button', 'setup-guide-chatbot__react-btn', emoji);
            btn.type = 'button';
            btn.setAttribute('aria-label', 'React with ' + emoji);
            btn.addEventListener('click', function () {
                reactions.querySelectorAll('.is-picked').forEach(function (b) {
                    b.classList.remove('is-picked');
                });
                btn.classList.add('is-picked');
                var existing = msg.querySelector('.setup-guide-chatbot__react-pill');
                if (existing) existing.remove();
                var pill = el('span', 'setup-guide-chatbot__react-pill', emoji + ' <span>Noted!</span>');
                msg.appendChild(pill);
                if (!opts.skipFeedback) {
                    self.flashBotReply(getReactionReply(emoji, !!self.activePageGuide, self.config.theme));
                }
            });
            reactions.appendChild(btn);
        });
        msg.appendChild(reactions);
    };

    SetupGuideChatbot.prototype.flashBotReply = function (text) {
        var self = this;
        if (self.busy) return;
        self.setBusy(true);
        self.showTyping();
        wait(TYPING_MS).then(function () {
            self.removeTyping();
            var msg = el('div', 'setup-guide-chatbot__msg setup-guide-chatbot__msg--bot');
            msg.appendChild(el('div', 'setup-guide-chatbot__bubble', escapeHtml(text)));
            self.messagesEl.appendChild(msg);
            scrollMessages(self.messagesEl);
            self.setBusy(false);
        });
    };

    SetupGuideChatbot.prototype.renderChips = function () {
        var self = this;
        this.chipsEl.innerHTML = '';
        this.steps.forEach(function (step, idx) {
            var chip = el('button', 'setup-guide-chatbot__chip');
            chip.type = 'button';
            chip.title = step.title || ('Step ' + (idx + 1));

            var num = el('span', 'setup-guide-chatbot__chip-num', String(step.id || idx + 1));
            chip.appendChild(num);

            var checklist = self.normalizeChecklist(step);
            var checklistId = self.resolveChecklistId(step, 'step-' + (step.id || idx + 1));
            if (self.isChecklistComplete(checklistId, checklist)) {
                chip.classList.add('is-complete');
                var tick = el('span', 'setup-guide-chatbot__chip-tick', '<i class="fas fa-check"></i>');
                chip.appendChild(tick);
            }

            if (idx === self.currentStep) chip.classList.add('is-active');
            chip.addEventListener('click', function () {
                if (!self.busy) self.showStep(idx, true);
            });
            self.chipsEl.appendChild(chip);
        });
    };

    SetupGuideChatbot.prototype.updateNav = function () {
        this.prevBtn.disabled = this.busy || this.currentStep <= 0;
        this.nextBtn.disabled = this.busy;
        this.chipsEl.querySelectorAll('.setup-guide-chatbot__chip').forEach(function (chip, i) {
            chip.classList.toggle('is-active', i === this.currentStep);
        }.bind(this));
        var step = this.steps[this.currentStep];
        this.nextBtn.textContent = this.currentStep >= this.steps.length - 1 ? 'Done' : 'Next step';
        if (step && step.title) {
            this.nextBtn.setAttribute('title', this.currentStep >= this.steps.length - 1 ? 'Finish setup guide' : ('Next: ' + step.title));
        }
        this.updateFooterLinks();
        if (this.pageHelpBtn) {
            this.pageHelpBtn.hidden = !(this.activePageGuide && this.isOnActiveGuidePage());
        }
    };

    SetupGuideChatbot.prototype.showPageGuide = function (guide, fromUser) {
        var self = this;
        if (!guide) return Promise.resolve();

        if (typeof guide.stepIndex === 'number') {
            self.currentStep = guide.stepIndex;
            self.renderChips();
            self.updateNav();
        }

        if (fromUser) {
            self.addUserMessage('Explain this page');
        }

        self.setBusy(true);
        self.showTyping();

        return wait(TYPING_MS + MSG_DELAY_MS).then(function () {
            self.removeTyping();
            var stepPayload = {
                pageTitle: guide.pageTitle || 'This page',
                message: guide.message || '',
                checklist: self.normalizeChecklist(guide),
                checklistId: guide.checklistId
            };
            self.addBotMessage(stepPayload, {
                skipFeedback: true,
                hideLinks: true,
                checklistId: guide.checklistId,
                stepIndex: guide.stepIndex
            });

            var step = self.steps[self.currentStep];
            if (step && !self.isOnActiveGuidePage()) {
                self.appendStepLinks(step, self.messagesEl.lastElementChild);
            }

            scrollMessages(self.messagesEl);
            self.setBusy(false);
            self.updateNav();
        });
    };

    SetupGuideChatbot.prototype.startGuide = function (isRestart) {
        var self = this;
        self.currentStep = 0;
        self.clearMessages();
        self.renderChips();
        if (isRestart) {
            self.addUserMessage('Full setup guide');
        }
        self.showWelcome().then(function () {
            return self.showStep(0, false);
        });
    };

    SetupGuideChatbot.prototype.showWelcome = function () {
        var self = this;
        self.setBusy(true);
        self.showTyping();
        return wait(TYPING_MS + 200).then(function () {
            self.removeTyping();
            var welcome = self.config.welcome || 'Hi! I can walk you through curriculum setup step by step.';
            var msg = el('div', 'setup-guide-chatbot__msg setup-guide-chatbot__msg--bot');
            msg.appendChild(el('div', 'setup-guide-chatbot__bubble', escapeHtml(welcome)));
            self.messagesEl.appendChild(msg);
            scrollMessages(self.messagesEl);
            self.setBusy(false);
        });
    };

    SetupGuideChatbot.prototype.finishGuide = function () {
        var self = this;
        self.addUserMessage('Finish setup');
        self.setBusy(true);
        self.showTyping();
        wait(TYPING_MS).then(function () {
            self.removeTyping();
            var msg = el('div', 'setup-guide-chatbot__msg setup-guide-chatbot__msg--bot');
            var n = self.steps.length;
            msg.appendChild(el(
                'div',
                'setup-guide-chatbot__bubble',
                escapeHtml(
                    'You have reviewed all ' + n + ' setup step' + (n === 1 ? '' : 's') +
                    '. Revisit any step with the numbers below, or use Full setup guide to start over.'
                )
            ));
            self.messagesEl.appendChild(msg);
            scrollMessages(self.messagesEl);
            self.setBusy(false);
            self.updateNav();
        });
    };

    SetupGuideChatbot.prototype.showStep = function (index, fromUser) {
        var self = this;
        var step = self.steps[index];
        if (!step) return Promise.resolve();

        self.currentStep = index;
        self.updateNav();

        if (fromUser) {
            self.addUserMessage('Step ' + (step.id || index + 1) + (step.title ? ': ' + step.title : ''));
        }

        self.setBusy(true);
        self.showTyping();

        return wait(TYPING_MS + MSG_DELAY_MS).then(function () {
            self.removeTyping();
            self.addBotMessage(step, {
                skipFeedback: true,
                checklistId: self.resolveChecklistId(step, 'step-' + (step.id || index + 1)),
                stepIndex: index
            });
            self.setBusy(false);
            self.updateNav();
        });
    };

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function getReactionReply(emoji, onPage, theme) {
        var finance = theme === 'accountant';
        var map = {
            '👍': onPage ? 'Good — complete the checklist on this page, then use Next step.' : 'Great — keep going! Use Next step when you are ready.',
            '✅': onPage ? 'Mark tasks done on screen, then move to the next setup step.' : 'Perfect. Mark that step done in the real page, then continue here.',
            '🎉': finance
                ? 'Awesome progress! Your finance setup is coming together.'
                : 'Awesome progress! You are building a solid academic setup.',
            '💡': onPage ? 'Tip: read each bullet on this page top to bottom.' : 'Tip: do these steps in order — later steps depend on earlier ones.',
            '🙌': finance
                ? 'You have got this! Confirm the financial year is open before heavy posting.'
                : 'You have got this! Ask your technician if a page is missing.'
        };
        return map[emoji] || 'Thanks for the feedback!';
    }

    function init() {
        var root = document.getElementById('setup-guide-chatbot');
        if (!root) return;
        var dataEl = document.getElementById('setup-guide-chatbot-config');
        var config = {};
        if (dataEl && dataEl.textContent) {
            try {
                config = JSON.parse(dataEl.textContent);
            } catch (e) {
                console.warn('Setup guide chatbot: invalid config', e);
            }
        }
        window.setupGuideChatbot = new SetupGuideChatbot(root, config);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
