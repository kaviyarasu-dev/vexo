import json
import re
import subprocess
from pathlib import Path
import pytest

JS_TUTORIAL_PATH = Path("static/js/guided_tutorial.js")
JS_GLOSSARY_PATH = Path("static/js/glossary.js")
JS_GLOSSARY_TOOLTIP_PATH = Path("static/js/glossary_tooltip.js")
CSS_EDUCATION_PATH = Path("static/css/education.css")


def test_education_assets_exist():
    """Verify all static assets for education layer exist."""
    assert JS_TUTORIAL_PATH.exists(), "guided_tutorial.js must exist"
    assert JS_GLOSSARY_PATH.exists(), "glossary.js must exist"
    assert JS_GLOSSARY_TOOLTIP_PATH.exists(), "glossary_tooltip.js must exist"
    assert CSS_EDUCATION_PATH.exists(), "education.css must exist"


def test_guided_tutorial_step_count_and_titles():
    """Verify guided_tutorial.js defines exactly 4 steps covering the specified user journey."""
    code = JS_TUTORIAL_PATH.read_text(encoding="utf-8")
    
    assert "totalSteps = 4" in code or "this.totalSteps = 4" in code or "stepNumber: 4" in code
    assert "The Universe" in code
    assert "The Setup" in code
    assert "The Result" in code
    assert "The Risk" in code


def test_guided_tutorial_skippable_and_local_storage():
    """Verify guided tutorial is skippable at any step and persists progress to localStorage."""
    code = JS_TUTORIAL_PATH.read_text(encoding="utf-8")
    
    assert "quant_tutorial_completed" in code
    assert "quant_tutorial_step" in code
    assert "skip()" in code or "skip ()" in code
    assert "Skip" in code


def test_tooltip_simple_mode_only_rule():
    """Verify glossary tooltip engine strictly enforces Simple Mode only."""
    code = JS_GLOSSARY_TOOLTIP_PATH.read_text(encoding="utf-8")
    assert "isSimpleMode" in code
    assert "mode-simple" in code or "quant_app_mode" in code


def test_tutorial_node_runtime_execution():
    """Execute guided_tutorial.js in Node.js with mock DOM to verify step 1 to 4 progression without errors."""
    node_test_script = """
    // Mock DOM environment
    const storage = {};
    global.localStorage = {
        getItem: (k) => storage[k] || null,
        setItem: (k, v) => { storage[k] = String(v); },
        removeItem: (k) => { delete storage[k]; }
    };

    const mockElement = () => ({
        style: {},
        classList: {
            add: () => {},
            remove: () => {},
            contains: () => false
        },
        querySelectorAll: () => [],
        querySelector: () => mockElement(),
        addEventListener: () => {},
        setAttribute: () => {},
        getBoundingClientRect: () => ({ top: 100, left: 100, right: 200, bottom: 200, width: 100, height: 100 })
    });

    global.document = {
        readyState: 'complete',
        getElementById: () => null,
        createElement: () => mockElement(),
        body: {
            appendChild: () => {},
            classList: { contains: () => false }
        },
        documentElement: {
            classList: { contains: () => false }
        },
        querySelector: () => mockElement(),
        querySelectorAll: () => [mockElement(), mockElement(), mockElement(), mockElement()],
        addEventListener: () => {}
    };

    global.window = {
        innerWidth: 1280,
        innerHeight: 800,
        addEventListener: () => {},
        localStorage: global.localStorage
    };

    // Load and evaluate guided_tutorial.js
    const fs = require('fs');
    const tutorialCode = fs.readFileSync('static/js/guided_tutorial.js', 'utf8');
    eval(tutorialCode);

    const controller = window.guidedTutorial;
    if (!controller) {
        throw new Error("window.guidedTutorial instance not found");
    }

    // Step 1: Universe
    controller.goToStep(1);
    if (controller.currentStep !== 1) throw new Error("Expected Step 1");

    // Advance to Step 2: Setup
    controller.next();
    if (controller.currentStep !== 2) throw new Error("Expected Step 2");

    // Advance to Step 3: Result
    controller.next();
    if (controller.currentStep !== 3) throw new Error("Expected Step 3");

    // Advance to Step 4: Risk
    controller.next();
    if (controller.currentStep !== 4) throw new Error("Expected Step 4");

    // Finish tour
    controller.next();
    if (global.localStorage.getItem('quant_tutorial_completed') !== 'true') {
        throw new Error("Expected quant_tutorial_completed === 'true'");
    }

    // Test Skip functionality
    controller.resetTutorial();
    controller.skip();
    if (global.localStorage.getItem('quant_tutorial_completed') !== 'true') {
        throw new Error("Expected skip to set quant_tutorial_completed === 'true'");
    }

    console.log("TUTORIAL_SIMULATION_SUCCESS");
    """

    res = subprocess.run(
        ["node", "-e", node_test_script],
        capture_output=True,
        text=True,
        check=True
    )
    assert "TUTORIAL_SIMULATION_SUCCESS" in res.stdout
