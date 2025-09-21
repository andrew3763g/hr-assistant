"""Utility script to send a test email using SMTP credentials from the environment."""
from __future__ import annotations

import argparse
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Sequence

from dotenv import load_dotenv

DEFAULT_RECIPIENT_ENV = "MAIL_SMOKE_RECIPIENT"
DEFAULT_USER_ENV = "EMAIL_USER"
DEFAULT_PASS_ENV = "EMAIL_PASS"
DEFAULT_SUBJECT = "Test from hr-assistant"
DEFAULT_BODY = "Hello from Gmail via app password."
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 465


@dataclass(frozen=True)
class Credentials:
    """Holds SMTP authentication details."""

    username: str
    password: str


@dataclass(frozen=True)
class SMTPSettings:
    """Configuration for connecting to an SMTP server."""

    host: str
    port: int
    use_ssl: bool = True


@dataclass(frozen=True)
class CliOptions:
    """Represents parsed command line options."""

    recipient: str
    subject: str
    body: str
    smtp_host: str
    smtp_port: int
    use_ssl: bool
    sender: str | None


def parse_args(argv: Sequence[str] | None = None) -> CliOptions:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--to",
        dest="recipient",
        default=os.getenv(DEFAULT_RECIPIENT_ENV),
        help=(
            "Email address to send the smoke test to. "
            f"Defaults to ${DEFAULT_RECIPIENT_ENV} if set."
        ),
    )
    parser.add_argument(
        "--subject",
        default=DEFAULT_SUBJECT,
        help="Subject line for the smoke test email.",
    )
    parser.add_argument(
        "--body",
        default=DEFAULT_BODY,
        help="Plaintext body for the smoke test email.",
    )
    parser.add_argument(
        "--smtp-host",
        default=DEFAULT_SMTP_HOST,
        help="Hostname of the SMTP server.",
    )
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=DEFAULT_SMTP_PORT,
        help="Port of the SMTP server.",
    )
    parser.add_argument(
        "--no-ssl",
        dest="use_ssl",
        action="store_false",
        help="Disable SMTP over SSL and use STARTTLS instead.",
    )
    parser.add_argument(
        "--sender",
        default=None,
        help="Override the sender address. Defaults to the authenticated user.",
    )

    namespace = parser.parse_args(argv)

    if not namespace.recipient:
        parser.error(
            "recipient is required. Provide --to or set the "
            f"${DEFAULT_RECIPIENT_ENV} environment variable."
        )

    return CliOptions(
        recipient=namespace.recipient,
        subject=namespace.subject,
        body=namespace.body,
        smtp_host=namespace.smtp_host,
        smtp_port=namespace.smtp_port,
        use_ssl=namespace.use_ssl,
        sender=namespace.sender,
    )


def _require_env(name: str, message: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(message)
    return value


def load_credentials(
    user_env: str = DEFAULT_USER_ENV, pass_env: str = DEFAULT_PASS_ENV
) -> Credentials:
    username = _require_env(
        user_env, f"Missing SMTP username. Set the {user_env} environment variable."
    )
    password = _require_env(
        pass_env, f"Missing SMTP password. Set the {pass_env} environment variable."
    )

    return Credentials(username=username, password=password)


def build_message(options: CliOptions, credentials: Credentials) -> EmailMessage:
    message = EmailMessage()
    sender = options.sender or credentials.username

    message["From"] = sender
    message["To"] = options.recipient
    message["Subject"] = options.subject
    message.set_content(options.body)

    return message


def send_message(
    message: EmailMessage, credentials: Credentials, settings: SMTPSettings
) -> None:
    context = ssl.create_default_context()
    if settings.use_ssl:
        with smtplib.SMTP_SSL(settings.host, settings.port, context=context) as smtp:
            smtp.login(credentials.username, credentials.password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.host, settings.port) as smtp:
            smtp.starttls(context=context)
            smtp.login(credentials.username, credentials.password)
            smtp.send_message(message)


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    options: CliOptions | None = None
    settings: SMTPSettings | None = None

    try:
        options = parse_args(argv)
        credentials = load_credentials()
        settings = SMTPSettings(
            host=options.smtp_host,
            port=options.smtp_port,
            use_ssl=options.use_ssl,
        )
        message = build_message(options, credentials)
        send_message(message, credentials, settings)
    except (RuntimeError, smtplib.SMTPException) as exc:
        print(f"Error sending test email: {exc}")
        return 1

    assert options is not None
    assert settings is not None
    print(
        "Test email sent to "
        f"{options.recipient} via {settings.host}:{settings.port}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
