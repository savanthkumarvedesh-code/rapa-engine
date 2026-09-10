"""
Tests for RAPA Autonomous Dynamic CAPTCHA Solver Module.
(src.rapa.ingestion.captcha_solver)
"""

import pytest
from unittest.mock import MagicMock, patch

from src.rapa.ingestion.captcha_solver import DynamicCaptchaHandler
from src.rapa.ingestion.dynamic_session_engine import DynamicSessionEngine


def test_detect_no_captcha():
    """Verify detect_captcha returns None when no CAPTCHA elements exist on page."""
    mock_page = MagicMock()
    mock_page.query_selector.return_value = None

    handler = DynamicCaptchaHandler()
    res = handler.detect_captcha(mock_page)
    assert res is None

    handle_res = handler.handle_and_solve_captcha(mock_page)
    assert handle_res["detected"] is False
    assert handle_res["solved"] is False
    assert handle_res["type"] == "NONE"


def test_detect_turnstile():
    """Verify detection of Cloudflare Turnstile challenge iframe."""
    mock_page = MagicMock()
    mock_elem = MagicMock()
    mock_elem.is_visible.return_value = True

    def query_mock(selector):
        if "challenges.cloudflare.com" in selector:
            return mock_elem
        return None

    mock_page.query_selector.side_effect = query_mock

    handler = DynamicCaptchaHandler()
    res = handler.detect_captcha(mock_page)
    assert res is not None
    assert res["type"] == "turnstile"
    assert "Turnstile" in res["description"]


def test_detect_recaptcha_v2():
    """Verify detection of Google reCAPTCHA v2 iframe."""
    mock_page = MagicMock()
    mock_elem = MagicMock()
    mock_elem.is_visible.return_value = True

    def query_mock(selector):
        if "recaptcha/api2/anchor" in selector:
            return mock_elem
        return None

    mock_page.query_selector.side_effect = query_mock

    handler = DynamicCaptchaHandler()
    res = handler.detect_captcha(mock_page)
    assert res is not None
    assert res["type"] == "recaptcha_v2"
    assert "reCAPTCHA" in res["description"]


def test_detect_image_ocr():
    """Verify detection of image CAPTCHA with input field."""
    mock_page = MagicMock()
    img_elem = MagicMock()
    img_elem.is_visible.return_value = True
    input_elem = MagicMock()
    input_elem.is_visible.return_value = True

    def query_mock(selector):
        if "img[src*='captcha']" in selector:
            return img_elem
        if "input[name*='captcha']" in selector:
            return input_elem
        return None

    mock_page.query_selector.side_effect = query_mock

    handler = DynamicCaptchaHandler()
    res = handler.detect_captcha(mock_page)
    assert res is not None
    assert res["type"] == "image_ocr"
    assert res["img_selector"] == "img[src*='captcha']"
    assert res["input_selector"] == "input[name*='captcha']"


def test_detect_slider():
    """Verify detection of puzzle slider element."""
    mock_page = MagicMock()
    slider_elem = MagicMock()
    slider_elem.is_visible.return_value = True

    def query_mock(selector):
        if ".slider-btn" in selector:
            return slider_elem
        return None

    mock_page.query_selector.side_effect = query_mock

    handler = DynamicCaptchaHandler()
    res = handler.detect_captcha(mock_page)
    assert res is not None
    assert res["type"] == "slider"


def test_solve_turnstile_bezier_simulation():
    """Verify humanized Bezier mouse trajectory click for Turnstile."""
    mock_page = MagicMock()
    mock_elem = MagicMock()
    mock_elem.bounding_box.return_value = {"x": 200, "y": 300, "width": 300, "height": 65}
    mock_page.query_selector.return_value = mock_elem

    handler = DynamicCaptchaHandler()
    challenge = {"type": "turnstile", "selector": "iframe[src*='turnstile']", "description": "Turnstile"}

    success = handler.solve_turnstile_or_recaptcha(mock_page, challenge)
    assert success is True
    assert mock_page.mouse.move.called
    assert mock_page.mouse.down.called
    assert mock_page.mouse.up.called


def test_solve_image_with_gemini_vision():
    """Verify image screenshot clipping, Gemini multimodal extraction, and typing into input."""
    mock_page = MagicMock()
    img_elem = MagicMock()
    img_elem.screenshot.return_value = b"\x89PNG\r\n\x1a\nfake_image_bytes"
    inp_elem = MagicMock()

    def query_mock(selector):
        if selector == "img.captcha":
            return img_elem
        if selector == "input.captcha":
            return inp_elem
        return None

    mock_page.query_selector.side_effect = query_mock

    handler = DynamicCaptchaHandler(gemini_api_key="mock_key")
    
    # Mock Gemini client response
    mock_gemini_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "7X9K2"
    mock_gemini_client.models.generate_content.return_value = mock_resp
    handler._genai_client = mock_gemini_client

    challenge = {
        "type": "image_ocr",
        "img_selector": "img.captcha",
        "input_selector": "input.captcha",
        "description": "Image Alphanumeric CAPTCHA",
    }

    success = handler.solve_image_or_math_captcha(mock_page, challenge)
    assert success is True
    assert inp_elem.fill.called
    assert inp_elem.type.called
    mock_page.keyboard.press.assert_called_with("Enter")


def test_solve_puzzle_slider():
    """Verify puzzle slider drag gesture."""
    mock_page = MagicMock()
    mock_elem = MagicMock()
    mock_elem.bounding_box.return_value = {"x": 100, "y": 200, "width": 40, "height": 40}
    mock_page.query_selector.return_value = mock_elem

    handler = DynamicCaptchaHandler()
    challenge = {"type": "slider", "selector": ".slider-btn"}

    success = handler.solve_puzzle_slider(mock_page, challenge, drag_distance=150)
    assert success is True
    assert mock_page.mouse.down.called
    assert mock_page.mouse.up.called


def test_dynamic_session_engine_has_captcha_handler():
    """Verify DynamicSessionEngine integrates DynamicCaptchaHandler."""
    engine = DynamicSessionEngine()
    assert hasattr(engine, "captcha_handler")
    assert isinstance(engine.captcha_handler, DynamicCaptchaHandler)
