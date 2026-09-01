"""Unit tests for WhatsApp automation and Address Book tools."""
import pytest
from backend.tools.whatsapp_tools import (
    call_whatsapp_contact,
    delete_contact,
    delete_whatsapp_message,
    get_contact,
    list_contacts,
    save_contact,
    send_active_message,
    send_whatsapp_message,
)


def test_save_and_get_contact():
    """Test saving and retrieving contacts from SQLite."""
    res_save = save_contact(name="Shivam", phone="9501445740", relationship="Self")
    assert res_save["status"] == "success"
    assert res_save["contact"]["name"] == "Shivam"

    res_get = get_contact(name="Shivam")
    assert res_get["status"] == "success"
    assert "9501445740" in res_get["contact"]["phone"]


def test_delete_contact():
    """Test deleting contact from SQLite."""
    save_contact(name="TemporaryContact", phone="9876500000")
    res_del = delete_contact(name="TemporaryContact")
    assert res_del["status"] == "success"
    assert "deleted" in res_del["message"]

    res_check = get_contact(name="TemporaryContact")
    assert res_check["status"] == "not_found"


def test_list_contacts():
    """Test listing saved contacts."""
    save_contact(name="Rahul", phone="+919876543211", relationship="Friend")
    res = list_contacts()
    assert res["status"] == "success"
    assert res["total_contacts"] >= 1


def test_send_whatsapp_message_with_contact(monkeypatch):
    """Test drafting WhatsApp message for a saved contact."""
    opened_links = []
    monkeypatch.setattr("os.startfile", lambda uri: opened_links.append(uri), raising=False)
    monkeypatch.setattr("webbrowser.open", lambda url, new=0, autoraise=True: opened_links.append(url))

    save_contact(name="Shivam", phone="9501445740")
    res = send_whatsapp_message(contact_or_phone="Shivam", message="kal mai nahi aaunga")
    assert res["status"] == "success"
    assert res["recipient"] == "Shivam"
    assert "whatsapp" in res["url"]
    assert len(opened_links) == 1


def test_send_active_message():
    """Test sending active drafted message shortcut."""
    res = send_active_message()
    assert res["status"] == "success"
    assert "Sent" in res["message"]


def test_delete_whatsapp_message():
    """Test message delete and draft clear."""
    res_draft = delete_whatsapp_message(mode="draft")
    assert res_draft["status"] in ["success", "unsupported"]

    res_last = delete_whatsapp_message(mode="last_sent")
    assert res_last["status"] in ["success", "unsupported"]


def test_send_whatsapp_message_direct_phone(monkeypatch):
    """Test drafting WhatsApp message with raw phone number."""
    opened_links = []
    monkeypatch.setattr("os.startfile", lambda uri: opened_links.append(uri), raising=False)
    monkeypatch.setattr("webbrowser.open", lambda url, new=0, autoraise=True: opened_links.append(url))

    res = send_whatsapp_message(contact_or_phone="+919876543210", message="Hello!")
    assert res["status"] == "success"
    assert "919876543210" in res["phone"]
    assert len(opened_links) == 1


def test_send_whatsapp_unknown_contact():
    """Test helpful response when contact is not in address book."""
    res = send_whatsapp_message(contact_or_phone="UnknownPerson999", message="Test")
    assert res["status"] == "contact_not_found"
    assert "don't have a phone number saved" in res["message"]


def test_call_whatsapp_contact(monkeypatch):
    """Test initiating WhatsApp voice call."""
    opened_links = []
    monkeypatch.setattr("os.startfile", lambda uri: opened_links.append(uri), raising=False)
    monkeypatch.setattr("webbrowser.open", lambda url, new=0, autoraise=True: opened_links.append(url))

    save_contact(name="Shivam", phone="9501445740")
    res = call_whatsapp_contact(contact_or_phone="Shivam", call_type="voice")
    assert res["status"] == "success"
    assert res["recipient"] == "Shivam"
    assert len(opened_links) == 1
