console.log('Loading editor.js');

var checkFormatLockTime = new Date();  // for template

/* Setup */
function trackTextChanges() {
  quill.on('text-change', function (delta, oldDelta, source) {
    if (source == 'silent') {
      return;
    }
    else {
      // Classify whether it's insert or delete
      eventName = null;
      eventSource = sourceToEventSource(source);

      ops = new Array();
      for (let i = 0; i < delta.ops.length; i++) {
        ops = ops.concat(Object.keys(delta.ops[i]));
      }
      if (ops.includes('insert')) {
        eventName = EventName.TEXT_INSERT;
      } else if (ops.includes('delete')) {
        eventName = EventName.TEXT_DELETE;
      } else {
        eventName = EventName.SKIP;
        console.log('Ignore format change');
      }
      logEvent(eventName, eventSource, textDelta = delta);

      if (isCounterEnabled == true) {
        updateCounter();
      }

      if (domain == 'template') {
        let currentTime = new Date();
        let elapsedTime = (currentTime - checkFormatLockTime) / 1000;

        if (elapsedTime > 1) {
          checkFormatLockTime = currentTime;
          formatNonTerminals();
        }
      }
    }
  });
}

function trackTextChangesByMachineOnly() {
  quill.on('text-change', function (delta, oldDelta, source) {
    eventName = null;
    eventSource = sourceToEventSource(source);

    ops = new Array();
    for (let i = 0; i < delta.ops.length; i++) {
      ops = ops.concat(Object.keys(delta.ops[i]));
    }
    if (ops.includes('insert')) {
      eventName = EventName.TEXT_INSERT;
    } else if (ops.includes('delete')) {
      eventName = EventName.TEXT_DELETE;
    } else {
      eventName = EventName.SKIP;
      console.log('Ignore format change');
    }

    // Ignore text-change by user and reset to oldDelta
    if (source == 'silent') {
      return;
    } else if (source == EventSource.API) {
      logEvent(eventName, eventSource, textDelta = delta);
      // Allow deletion
    } else if (source == EventSource.USER && eventName == EventName.TEXT_DELETE) {
      logEvent(eventName, eventSource, textDelta = delta);
      // Allow insertion of whitespace
    } else if (source == EventSource.USER && eventName == EventName.TEXT_INSERT) {
      const isInsert = (element) => element == 'insert';
      let index = ops.findIndex(isInsert);

      if (delta.ops[index]['insert'].trim() == '') {
        logEvent(eventName, eventSource, textDelta = delta);
      } else {
        quill.setContents(oldDelta, 'silent');
      }
    } else {
      console.log('Ignore unknown change:', source, eventName);
    }

    if (isCounterEnabled == true) {
      updateCounter();
    }

  });
}

function trackSelectionChange() {
  // NOTE It's "silenced" when coincide with text-change
  quill.on('selection-change', function (range, oldRange, source) {
    if (range === null) {
      return;  // click outside of the editor
    } else if (source == 'silent') {
      return;
    } else {
      eventName = null;
      eventSource = sourceToEventSource(source);

      // Use prevCursorIndex instead of oldRange.index as oldRange is null at times
      if (range.length > 0) {
        eventName = EventName.CURSOR_SELECT;
      } else if (range.index > prevCursorIndex) {
        eventName = EventName.CURSOR_FORWARD;
      } else if (range.index < prevCursorIndex) {
        eventName = EventName.CURSOR_BACKWARD;
      } else if (range.index == prevCursorIndex) {
        // Deselect
        eventName = EventName.SKIP;
      } else {
        if (debug) {
          alert('Wrong selection-change handling!');
          console.log(range, oldRange, source);
        }
        eventName = EventName.SKIP;
      }

      logEvent(eventName, eventSource, textDelta = '', cursorRange = range);
    }
  });
}

function trackParsingTrigger() {
  let lastCursorIndex = 0;  // Store the last cursor position

  // This is an example of a function that can be used to trigger parsing of the logs
  quill.on('selection-change', function (range, oldRange, source) {
    if (range === null) {
      console.log('Range is null');
      return;  // click outside of the editor
    } else if (source == 'silent') {
      console.log('Source is silent');
      return;
    } else {
      eventName = null;
      eventSource = sourceToEventSource(source);

      console.log('Selection change:', {
        range: range,
        oldRange: oldRange,
        source: source,
        currentIndex: range.index,
        lastIndex: lastCursorIndex
      });

      // Check if cursor moved backwards
      if (range.length <= 0 && range.index < lastCursorIndex) {
        console.log('Triggering parse_logs - cursor moved backwards');
        parse_logs();
      } else if (debug) {
        alert('Wrong selection-change handling!');
        console.log(range, oldRange, source);
      }

      // Update the last cursor position after checking
      lastCursorIndex = range.index;
    }
  });
}

function setupEditorHumanOnly() {
  console.log('Setting up editor in human-only mode');

  quill = new Quill('#editor-container', {
    theme: 'snow',
    placeholder: 'Write something...',
    modules: {
      clipboard: {
        matchVisual: false,  // Prevent empty paragraph to be added
        matchers: [
          [
            Node.ELEMENT_NODE, function (node, delta) {
              return delta.compose(new Delta().retain(delta.length(), {
                color: false,
                background: false,
                bold: false,
                strike: false,
                underline: false
              }));
            }
          ]
        ]
      },
    }
  });

  console.log('Setting up event handlers');
  trackTextChanges();
  trackSelectionChange();
  trackParsingTrigger();
  console.log('Event handlers setup complete');

  quill.focus();
}

function setupEditorMachineOnly() {
  let bindings = {
    tab: {
      key: 9,
      handler: function () {
        logEvent(EventName.SUGGESTION_GET, EventSource.USER);
        queryGPT3();
      }
    },
    enter: {
      key: 13,
      handler: function () {
        let selectedItem = $('.sudo-hover');
        if (selectedItem.length > 0) {
          $(selectedItem).click();
        } else {
          return true;
        }
      }
    }
  };

  quill = new Quill('#editor-container', {
    theme: 'snow',
    modules: {
      keyboard: {
        bindings: bindings
      },
      clipboard: {
        matchVisual: false,  // Prevent empty paragraph to be added
        matchers: [
          [
            Node.ELEMENT_NODE, function (node, delta) {
              return delta.compose(new Delta().retain(delta.length(), {
                color: false,
                background: false,
                bold: false,
                strike: false,
                underline: false
              }));
            }
          ]
        ]
      },
    }
  });

  trackTextChangesByMachineOnly();
  trackSelectionChange();

  quill.focus();
}

function setupEditor() {
  let bindings = {
    tab: {
      key: 9,
      handler: function () {
        logEvent(EventName.SUGGESTION_GET, EventSource.USER);
        queryGPT3();
      }
    },
    enter: {
      key: 13,
      handler: function () {
        let selectedItem = $('.sudo-hover');
        if (selectedItem.length > 0) {
          $(selectedItem).click();
        } else {
          return true;
        }
      }
    }
  };

  quill = new Quill('#editor-container', {
    theme: 'snow',
    modules: {
      keyboard: {
        bindings: bindings
      },
      clipboard: {
        matchVisual: false,  // Prevent empty paragraph to be added
        matchers: [
          [
            Node.ELEMENT_NODE, function (node, delta) {
              return delta.compose(new Delta().retain(delta.length(), {
                color: false,
                background: false,
                bold: false,
                strike: false,
                underline: false
              }));
            }
          ]
        ]
      },
    }
  });

  trackTextChanges();
  trackSelectionChange();
  trackParsingTrigger();

  quill.focus();
}

/* Cursor */
function getCursorIndex() {
  let range = quill.getSelection();
  let currentIndex = prevCursorIndex; // Store the current prevCursorIndex before updating

  if (range) {
    if (range.length == 0) {
      console.log('Updating prevCursorIndex:', { old: prevCursorIndex, new: range.index });
      prevCursorIndex = range.index;
      return { current: range.index, previous: currentIndex };
    } else {
      // For selection, return index of beginning of selection
      console.log('Updating prevCursorIndex for selection:', { old: prevCursorIndex, new: range.index });
      prevCursorIndex = range.index;
      return { current: range.index, previous: currentIndex }; // Selection
    }
  } else {
    console.log('No range, using prevCursorIndex:', prevCursorIndex);
    return { current: prevCursorIndex, previous: currentIndex }; // Not in editor
  }
}

function setCursor(index) {
  // Adjust if index is outside of range
  let doc = quill.getText(0);
  let lastIndex = doc.length - 1;
  if (lastIndex < index) {
    index = lastIndex;
  }

  quill.setSelection(index);
  prevCursorIndex = index;
}

function setCursorAtTheEnd() {
  // If it's not triggerd by user's text insertion, and instead by api's
  // forced selection change, then it is saved as part of logs by selection-change
  let doc = quill.getText(0);
  let index = doc.length - 1; // The end of doc
  setCursor(index);
}

/* Text */
function getText() {
  let text = quill.getText(0);
  return text.substring(0, text.length - 1);  // Exclude trailing \n
}

function setText(text) {
  // NOTE Does not keep the formating
  quill.setText(text, 'api');
  setCursor(text.length);
}

function appendText(text) {
  let lastIndex = getText().length;

  // This action is automatically logged by text-change
  quill.insertText(lastIndex, text);

  // By default, selection change due to text insertion is "silent"
  // and not saved as part of logs
  setCursorAtTheEnd();
}
