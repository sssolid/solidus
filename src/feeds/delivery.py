# src/feeds/delivery.py
import ftplib
import logging
import os

import paramiko
import requests

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger("solidus.feeds")


class BaseDeliveryHandler:
    """Base class for feed delivery handlers"""

    def __init__(self, feed):
        self.feed = feed
        self.config = feed.delivery_config or {}

    def deliver(self, generation):
        """Deliver the generated feed"""
        raise NotImplementedError

    def get_file_content(self, file_path):
        """Get file content from storage"""
        try:
            with default_storage.open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise


class EmailDeliveryHandler(BaseDeliveryHandler):
    """Deliver feeds via email"""

    def deliver(self, generation):
        try:
            # Get email configuration
            recipient_email = self.config.get("email", self.feed.customer.email)
            cc_emails = self.config.get("cc_emails", [])
            subject_template = self.config.get(
                "subject_template", "Your {feed_name} is ready"
            )

            # Build email
            subject = subject_template.format(
                feed_name=self.feed.name,
                feed_type=self.feed.get_feed_type_display(),
                date=generation.started_at.strftime("%Y-%m-%d"),
            )

            # Render email body
            context = {
                "feed": self.feed,
                "generation": generation,
                "customer": self.feed.customer,
                "download_url": f"{settings.BASE_URL}/feeds/download/{generation.generation_id}/",
            }

            html_content = render_to_string("feeds/email/feed_ready.html", context)
            text_content = render_to_string("feeds/email/feed_ready.txt", context)

            # Create email
            email = EmailMessage(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
                cc=cc_emails,
            )
            email.attach_alternative(html_content, "text/html")

            # Attach file if it's small enough
            if (
                generation.file_size and generation.file_size < 10 * 1024 * 1024
            ):  # 10MB limit
                file_content = self.get_file_content(generation.file_path)
                filename = os.path.basename(generation.file_path)
                email.attach(filename, file_content)

            # Send email
            email.send()

            return {
                "success": True,
                "details": {
                    "recipient": recipient_email,
                    "cc": cc_emails,
                    "attached": generation.file_size < 10 * 1024 * 1024
                    if generation.file_size
                    else False,
                },
            }

        except Exception as e:
            logger.error(f"Email delivery error: {str(e)}")
            return {"success": False, "error": str(e)}


class FTPDeliveryHandler(BaseDeliveryHandler):
    """Deliver feeds via FTP"""

    def deliver(self, generation):
        ftp = None
        try:
            # Get FTP configuration
            host = self.config.get("host")
            port = self.config.get("port", 21)
            username = self.config.get("username")
            password = self.config.get("password")
            remote_path = self.config.get("remote_path", "/")

            if not all([host, username, password]):
                raise ValueError("Missing FTP configuration")

            # Connect to FTP server
            ftp = ftplib.FTP()
            ftp.connect(host, port)
            ftp.login(username, password)

            # Change to remote directory
            if remote_path and remote_path != "/":
                try:
                    ftp.cwd(remote_path)
                except ftplib.error_perm:
                    # Try to create directory if it doesn't exist
                    self._create_ftp_path(ftp, remote_path)
                    ftp.cwd(remote_path)

            # Upload file
            file_content = self.get_file_content(generation.file_path)
            filename = os.path.basename(generation.file_path)

            # Use binary mode for all file types
            ftp.storbinary(f"STOR {filename}", file_content)

            # Close connection
            ftp.quit()

            return {
                "success": True,
                "details": {
                    "host": host,
                    "remote_path": os.path.join(remote_path, filename),
                    "size": len(file_content),
                },
            }

        except Exception as e:
            logger.error(f"FTP delivery error: {str(e)}")
            if ftp:
                try:
                    ftp.quit()
                except Exception as e:
                    logger.error(f"FTP delivery error: {str(e)}")
                    pass
            return {"success": False, "error": str(e)}

    def _create_ftp_path(self, ftp, path):
        """Create FTP directory path recursively"""
        dirs = path.strip("/").split("/")
        for i in range(len(dirs)):
            dir_path = "/".join(dirs[: i + 1])
            try:
                ftp.mkd(dir_path)
            except ftplib.error_perm:
                # Directory might already exist
                pass


class SFTPDeliveryHandler(BaseDeliveryHandler):
    """Deliver feeds via SFTP"""

    def deliver(self, generation):
        sftp = None
        transport = None

        try:
            # Get SFTP configuration
            host = self.config.get("host")
            port = self.config.get("port", 22)
            username = self.config.get("username")
            password = self.config.get("password")
            private_key_path = self.config.get("private_key_path")
            remote_path = self.config.get("remote_path", "/")

            if not host or not username:
                raise ValueError("Missing SFTP configuration")

            # Create SSH transport
            transport = paramiko.Transport((host, port))

            # Authenticate
            if private_key_path:
                # Use key-based authentication
                private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
                transport.connect(username=username, pkey=private_key)
            elif password:
                # Use password authentication
                transport.connect(username=username, password=password)
            else:
                raise ValueError("No authentication method provided")

            # Create SFTP client
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Create remote directory if needed
            if remote_path and remote_path != "/":
                self._create_sftp_path(sftp, remote_path)

            # Upload file
            file_content = self.get_file_content(generation.file_path)
            filename = os.path.basename(generation.file_path)
            remote_file_path = os.path.join(remote_path, filename)

            # Write file
            with sftp.open(remote_file_path, "wb") as remote_file:
                remote_file.write(file_content)

            # Close connections
            sftp.close()
            transport.close()

            return {
                "success": True,
                "details": {
                    "host": host,
                    "remote_path": remote_file_path,
                    "size": len(file_content),
                },
            }

        except Exception as e:
            logger.error(f"SFTP delivery error: {str(e)}")
            if sftp:
                sftp.close()
            if transport:
                transport.close()
            return {"success": False, "error": str(e)}

    def _create_sftp_path(self, sftp, path):
        """Create SFTP directory path recursively"""
        dirs = path.strip("/").split("/")
        current_path = ""

        for dir_name in dirs:
            current_path = os.path.join(current_path, dir_name)
            try:
                sftp.stat(current_path)
            except FileNotFoundError:
                try:
                    sftp.mkdir(current_path)
                except Exception as e:
                    logger.error(f"SFTP delivery error: {str(e)}")
                    pass


class WebhookDeliveryHandler(BaseDeliveryHandler):
    """Deliver feed notifications via webhook"""

    def deliver(self, generation):
        try:
            # Get webhook configuration
            webhook_url = self.config.get("webhook_url")
            auth_token = self.config.get("auth_token")
            include_file_url = self.config.get("include_file_url", True)
            method = self.config.get("method", "POST").upper()

            if not webhook_url:
                raise ValueError("Missing webhook URL")

            # Build payload
            payload = {
                "feed_id": str(self.feed.id),
                "feed_name": self.feed.name,
                "feed_type": self.feed.feed_type,
                "generation_id": str(generation.generation_id),
                "status": "completed",
                "row_count": generation.row_count,
                "file_size": generation.file_size,
                "generated_at": generation.completed_at.isoformat()
                if generation.completed_at
                else None,
                "customer": {
                    "id": self.feed.customer.id,
                    "username": self.feed.customer.username,
                    "company": self.feed.customer.company_name,
                },
            }

            if include_file_url:
                payload[
                    "download_url"
                ] = f"{settings.BASE_URL}/feeds/download/{generation.generation_id}/"

            # Build headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Solidus/1.0",
            }

            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            # Add custom headers if configured
            custom_headers = self.config.get("custom_headers", {})
            headers.update(custom_headers)

            # Send webhook
            if method == "POST":
                response = requests.post(
                    webhook_url, json=payload, headers=headers, timeout=30
                )
            else:
                response = requests.get(
                    webhook_url, params=payload, headers=headers, timeout=30
                )

            # Check response
            response.raise_for_status()

            return {
                "success": True,
                "details": {
                    "webhook_url": webhook_url,
                    "status_code": response.status_code,
                    "response": response.text[:500] if response.text else None,
                },
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook delivery error: {str(e)}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Webhook configuration error: {str(e)}")
            return {"success": False, "error": str(e)}


class DownloadDeliveryHandler(BaseDeliveryHandler):
    """Handler for direct download - just marks as ready"""

    def deliver(self, generation):
        # For download delivery, we just need to mark it as ready
        # The file is already generated and stored
        return {
            "success": True,
            "details": {
                "method": "download",
                "file_path": generation.file_path,
                "ready_for_download": True,
            },
        }


class DeliveryHandlerFactory:
    """Factory to get appropriate delivery handler"""

    handlers = {
        "download": DownloadDeliveryHandler,
        "email": EmailDeliveryHandler,
        "ftp": FTPDeliveryHandler,
        "sftp": SFTPDeliveryHandler,
        "api": WebhookDeliveryHandler,
    }

    @classmethod
    def get_handler(cls, feed):
        """Get delivery handler instance for feed"""
        handler_class = cls.handlers.get(feed.delivery_method)
        if not handler_class:
            raise ValueError(f"Unsupported delivery method: {feed.delivery_method}")

        return handler_class(feed)
