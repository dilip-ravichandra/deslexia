(() => {
  'use strict';

  const button = document.getElementById('adapt-paragraph');
  const rewriteButton = document.getElementById('rewrite-paragraph');
  const result = document.getElementById('paragraph-result');
  const status = document.getElementById('paragraph-status');
  const category = document.getElementById('paragraph-category');
  const style = document.getElementById('paragraph-style');
  let currentParagraph = '';
  let currentStart = 0;
  let generation = 0;

  function element(tag, content, className) {
    const node = document.createElement(tag);
    node.textContent = content;
    if (className) node.className = className;
    return node;
  }

  function show(data) {
    currentParagraph = data.original;
    result.replaceChildren();
    result.append(element('h3', 'Your paragraph, with support'));
    const sources = {
      learner_choice: 'You chose this help type.',
      learner_history: 'Chosen from repeated relevant requests in your saved profile.',
      starting_survey: 'Chosen from your starting profile.',
      default_layout: 'Sentence spacing is the starting view.'
    };
    result.append(element('p', sources[data.source] || sources.default_layout, 'paragraph-source'));
    const comparison = element('div', '', 'paragraph-comparison');
    const original = element('section', '', 'paragraph-pane');
    original.append(element('h4', 'Original'), element('p', data.original, 'paragraph-text'));
    const supported = element('section', '', 'paragraph-pane');
    supported.append(element('h4', 'Supported view'));
    if (data.category === 'SYNTACTIC' && data.style === 'steps') {
      const list = document.createElement('ol');
      data.sentences.forEach(sentence => list.append(element('li', sentence.trim())));
      supported.append(list);
    } else if (data.category === 'SYNTACTIC') {
      data.sentences.forEach(sentence => supported.append(element('p', sentence.trim(), 'paragraph-text')));
    } else {
      supported.append(element('p', data.original, 'paragraph-text'));
    }
    if (data.category === 'VOCABULARY') {
      supported.append(element('h4', 'Word notes'));
      if (data.glossary.length) {
        const list = document.createElement('ul');
        const notes = data.style === 'short' ? data.glossary.slice(0, 3) : data.glossary;
        notes.forEach(note => list.append(element('li', `${note.word}: ${note.meaning}`)));
        supported.append(list);
      } else supported.append(element('p', 'No reviewed word note is available for this paragraph. Select a word to ask for help.'));
    }
    if (data.category === 'CONCEPTUAL') {
      const list = document.createElement('ul');
      const prompts = data.style === 'short' ? data.prompts.slice(0, 1) : data.prompts;
      prompts.forEach(prompt => list.append(element('li', prompt)));
      supported.append(element('h4', 'Questions to explore'), list);
    }
    if (data.style === 'example') supported.append(element('p', data.source_example ? `Example in your text: ${data.source_example}` : 'No explicit example appears in this paragraph.'));
    comparison.append(original, supported);
    const ask = element('button', 'Ask about selected words', 'button');
    ask.type = 'button';
    ask.addEventListener('click', () => {
      const selection = window.getSelection();
      const selected = selection?.toString().trim() || '';
      const paragraphOffset = currentParagraph.indexOf(selected);
      if (!selected || selected.length > 300 || paragraphOffset < 0 || !result.contains(selection.anchorNode) || !result.contains(selection.focusNode)) {
        status.textContent = 'Select up to 300 characters from the paragraph view, then try again.';
        return;
      }
      setSelection({span: selected, start: currentStart + paragraphOffset});
      document.getElementById('go').focus();
      status.textContent = 'Choose the help type on the right, then press Help me understand.';
    });
    result.append(comparison, ask, element('p', data.category === 'VOCABULARY'
      ? 'The original words and order stay the same. Word notes come from a small unreviewed glossary; check them against the passage. Select source text here to ask for specific help.'
      : 'The original words and order stay the same. Select source text here and ask for specific help whenever you need it.', 'paragraph-note'));
    result.classList.remove('hidden');
    result.focus();
  }

  function showRewrite(data) {
    currentParagraph = data.original;
    result.replaceChildren();
    result.append(element('h3', 'Easier version, sentence by sentence'));
    result.append(element('p', data.changed_count
      ? `${data.changed_count} sentence${data.changed_count === 1 ? '' : 's'} changed. Highlighted words show what differs.`
      : 'No safe wording change was available for this paragraph. The original stays in place.', 'paragraph-source'));
    const sources = {
      learner_choice: 'This help type was your choice.',
      learner_history: 'This help type came from repeated requests for words in this paragraph.',
      starting_survey: 'This help type came from your starting profile.',
      default_layout: 'Sentence help is the starting choice.'
    };
    result.append(element('p', sources[data.source], 'paragraph-source'));
    data.sentences.forEach((sentence, index) => {
      const pair = element('section', '', 'paragraph-comparison paragraph-rewrite-row');
      const original = element('div', '', 'paragraph-pane');
      const adapted = element('div', '', 'paragraph-pane');
      original.append(element('h4', `Original sentence ${index + 1}`));
      adapted.append(element('h4', sentence.changed ? 'Easier version' : 'Kept original'));
      for (const [pane, parts, className] of [
        [original, sentence.original_parts, 'paragraph-original-change'],
        [adapted, sentence.adapted_parts, 'paragraph-adapted-change']
      ]) {
        const text = element('p', '', 'paragraph-text');
        parts.forEach(part => text.append(element(part.changed ? 'mark' : 'span', part.text, part.changed ? className : '')));
        pane.append(text);
      }
      adapted.append(element('p', sentence.reason, 'paragraph-note'));
      if (sentence.changed && sentence.checks) {
        const details = document.createElement('details');
        details.append(element('summary', 'Checks used for this sentence'));
        details.append(element('p', `Checked: ${sentence.checks.checks_run.join(', ')}.`, 'paragraph-note'));
        if (sentence.checks.checks_unavailable.length) details.append(element('p',
          `Unavailable: ${sentence.checks.checks_unavailable.map(check => check.check).join(', ')}.`, 'paragraph-note'));
        details.append(element('p', 'Passing checks does not prove the meaning is unchanged.', 'paragraph-note'));
        adapted.append(details);
      }
      pair.append(original, adapted);
      result.append(pair);
    });
    const back = element('button', 'Back to original', 'button');
    back.type = 'button';
    back.addEventListener('click', () => {
      result.classList.add('hidden');
      document.getElementById('reader').focus();
      status.textContent = 'Original text is ready.';
    });
    result.append(back, element('p', data.note, 'paragraph-note'));
    result.classList.remove('hidden');
    result.focus();
  }

  async function requestParagraph(path, render, pending, complete) {
    const paragraph = document.querySelector('#reader .para.active') || document.querySelector('#reader .para');
    const text = paragraph?.textContent || '';
    if (!text.trim()) {
      status.textContent = 'Open a paragraph first.';
      return;
    }
    if (text.length > 3000) {
      status.textContent = 'This paragraph is too long. Split it into smaller paragraphs with Enter, then try again.';
      return;
    }
    const paragraphs = Array.from(document.querySelectorAll('#reader .para'));
    const paragraphStart = paragraphs.slice(0, paragraphs.indexOf(paragraph)).reduce((offset, node) => offset + node.textContent.length, 0);
    const requestGeneration = ++generation;
    button.disabled = true;
    rewriteButton.disabled = true;
    status.textContent = pending;
    try {
      const headers = {'Content-Type': 'application/json'};
      const key = window.daReaderKey?.();
      if (key) headers['x-learner-key'] = key;
      const response = await fetch(path, {
        method: 'POST', headers,
        body: JSON.stringify({paragraph: text, document_language: window.LEARNER?.language() || 'en', category: category.value, style: style.value})
      });
      const data = await response.json();
      if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Paragraph support is unavailable.');
      if (requestGeneration !== generation) return;
      currentStart = paragraphStart;
      render(data);
      status.textContent = complete;
    } catch (error) {
      if (requestGeneration === generation) status.textContent = error.message;
    } finally {
      button.disabled = false;
      rewriteButton.disabled = false;
    }
  }

  button.addEventListener('click', () => requestParagraph('/api/paragraph-support', show,
    'Preparing your paragraph view…', 'Supported view ready. The original remains available.'));
  rewriteButton.addEventListener('click', () => requestParagraph('/api/paragraph-rewrite', showRewrite,
    'Checking possible wording changes…', 'Easier version ready. Compare every highlighted change with the original.'));

  window.addEventListener('passage-changed', () => {
    generation++;
    result.replaceChildren();
    result.classList.add('hidden');
    status.textContent = '';
    currentParagraph = '';
  });
})();
