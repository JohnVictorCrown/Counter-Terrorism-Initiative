package mail

import (
	"crypto/tls"
	"encoding/base64"
	"fmt"
	"mime"
	"mime/multipart"
	"net/smtp"
	"net/textproto"
	"os"
	"strings"

	"counter-terrorism-initiative/internal/db"
)

const maxAttachmentSize = 20 * 1024 * 1024

type SendResult struct {
	Success    bool   `json:"success"`
	To         string `json:"to"`
	Subject    string `json:"subject"`
	Attachment string `json:"attachment,omitempty"`
	Error      string `json:"error,omitempty"`
}

func SendEmail(to, subject, body string, fileData []byte, fileName string) *SendResult {
	password, err := db.LoadAppPassword()
	if err != nil || password == "" {
		return &SendResult{Error: "Gmail app password not found. Run 'crm store-password' first."}
	}

	if !strings.Contains(to, "@") || strings.Count(to, "@") != 1 {
		return &SendResult{Error: fmt.Sprintf("Invalid email address: %s", to)}
	}
	parts := strings.Split(to, "@")
	if len(parts) != 2 || !strings.Contains(parts[1], ".") {
		return &SendResult{Error: fmt.Sprintf("Invalid email address: %s", to)}
	}

	var msg string
	if fileName != "" && len(fileData) > 0 {
		if len(fileData) > maxAttachmentSize {
			return &SendResult{Error: "File too large. Maximum size is 20MB."}
		}
		msg = buildMultipartMessage(to, subject, body, fileData, fileName)
	} else {
		msg = buildPlainMessage(to, subject, body)
	}

	if err := sendViaSMTP(to, msg, password); err != nil {
		return &SendResult{Error: fmt.Sprintf("Failed to send email: %s", err.Error())}
	}

	return &SendResult{Success: true, To: to, Subject: subject, Attachment: fileName}
}

func SendBulkEmail(emails []string, subject, body string) (int, string) {
	password, err := db.LoadAppPassword()
	if err != nil || password == "" {
		return 0, "Gmail app password not found. Run 'crm store-password' first."
	}

	var validEmails []string
	for _, e := range emails {
		e = strings.TrimSpace(e)
		if strings.Count(e, "@") == 1 {
			parts := strings.Split(e, "@")
			if strings.Contains(parts[1], ".") {
				validEmails = append(validEmails, e)
			}
		}
	}

	if len(validEmails) == 0 {
		return 0, "No valid email addresses"
	}

	msg := buildBulkMessage(subject, body)
	for _, e := range validEmails {
		msg = strings.Replace(msg, "$TO$", e, 1)
	}

	hdr := make(textproto.MIMEHeader)
	hdr.Set("From", fmt.Sprintf("John Victor @ WaterParty <%s>", db.GmailAddr))
	hdr.Set("To", db.GmailAddr)
	hdr.Set("Subject", subject)
	hdr.Set("Bcc", strings.Join(validEmails, ", "))

	// Build a simple MIME message for BCC
	fullMsg := buildBulkMessage(subject, body)

	if err := sendViaSMTPBCC(validEmails, fullMsg, password); err != nil {
		return 0, fmt.Sprintf("Failed to send email: %s", err.Error())
	}

	return len(validEmails), ""
}

type SendCLIResult struct {
	Success  bool
	Count    int
	Error    string
	Attachments []string
}

func SendMailCLI(recipients []string, subject, body, fromName string, attachments []string) *SendCLIResult {
	password, err := db.LoadAppPassword()
	if err != nil || password == "" {
		return &SendCLIResult{Error: "Gmail app password not found. Run 'crm store-password' first."}
	}

	// Validate emails
	var validEmails []string
	for _, e := range recipients {
		e = strings.TrimSpace(e)
		if strings.Count(e, "@") == 1 {
			parts := strings.Split(e, "@")
			if len(parts[0]) > 0 && strings.Contains(parts[1], ".") && !strings.Contains(e, " ") {
				validEmails = append(validEmails, e)
			}
		}
	}

	if len(validEmails) == 0 {
		return &SendCLIResult{Error: "No valid email addresses"}
	}

	// Build MIME message
	var b strings.Builder
	from := fmt.Sprintf("%s <%s>", fromName, db.GmailAddr)
	b.WriteString(fmt.Sprintf("From: %s\r\n", from))
	b.WriteString(fmt.Sprintf("To: %s\r\n", db.GmailAddr))
	b.WriteString(fmt.Sprintf("Subject: %s\r\n", mime.QEncoding.Encode("utf-8", subject)))
	b.WriteString("MIME-Version: 1.0\r\n")

	if len(attachments) > 0 {
		writer := multipart.NewWriter(&b)
		boundary := writer.Boundary()
		b.WriteString(fmt.Sprintf("Content-Type: multipart/mixed; boundary=\"%s\"\r\n", boundary))
		b.WriteString("\r\n")

		// Text body part
		textWriter, _ := writer.CreatePart(textproto.MIMEHeader{
			"Content-Type": {"text/plain; charset=\"utf-8\""},
		})
		textWriter.Write([]byte(body))

		// Attachment parts
		for _, fpath := range attachments {
			data, err := os.ReadFile(fpath)
			if err != nil {
				return &SendCLIResult{Error: fmt.Sprintf("Cannot read attachment '%s': %v", fpath, err)}
			}
			if len(data) > maxAttachmentSize {
				return &SendCLIResult{Error: fmt.Sprintf("Attachment '%s' too large. Maximum is 20MB.", fpath)}
			}

			contentType := "application/octet-stream"
			if idx := strings.LastIndex(fpath, "."); idx >= 0 {
				if ct := mime.TypeByExtension(fpath[idx:]); ct != "" {
					contentType = ct
				}
			}

			// Extract just the filename
			_, fileName := fpath, fpath
			if idx := strings.LastIndexAny(fpath, "\\/"); idx >= 0 {
				fileName = fpath[idx+1:]
			}

			attachWriter, _ := writer.CreatePart(textproto.MIMEHeader{
				"Content-Type":              {contentType},
				"Content-Disposition":       {fmt.Sprintf("attachment; filename=\"%s\"", fileName)},
				"Content-Transfer-Encoding": {"base64"},
			})
			encoded := base64.StdEncoding.EncodeToString(data)
			attachWriter.Write([]byte(encoded))
		}

		writer.Close()
	} else {
		b.WriteString("Content-Type: text/plain; charset=\"utf-8\"\r\n")
		b.WriteString("\r\n" + body)
	}

	msg := b.String()

	if err := smtpSendBCC(validEmails, msg, password); err != nil {
		return &SendCLIResult{Error: fmt.Sprintf("Failed to send email: %s", err.Error())}
	}

	return &SendCLIResult{
		Success:     true,
		Count:       len(validEmails),
		Attachments: attachments,
	}
}

func buildPlainMessage(to, subject, body string) string {
	msg := fmt.Sprintf("From: John Victor @ WaterParty <%s>\r\n", db.GmailAddr)
	msg += fmt.Sprintf("To: %s\r\n", to)
	msg += fmt.Sprintf("Subject: %s\r\n", mime.QEncoding.Encode("utf-8", subject))
	msg += "MIME-Version: 1.0\r\n"
	msg += "Content-Type: text/plain; charset=\"utf-8\"\r\n"
	msg += "\r\n" + body
	return msg
}

func buildMultipartMessage(to, subject, body string, fileData []byte, fileName string) string {
	var b strings.Builder
	b.WriteString(fmt.Sprintf("From: John Victor @ WaterParty <%s>\r\n", db.GmailAddr))
	b.WriteString(fmt.Sprintf("To: %s\r\n", to))
	b.WriteString(fmt.Sprintf("Subject: %s\r\n", mime.QEncoding.Encode("utf-8", subject)))
	b.WriteString("MIME-Version: 1.0\r\n")

	writer := multipart.NewWriter(&b)
	boundary := writer.Boundary()
	b.WriteString(fmt.Sprintf("Content-Type: multipart/mixed; boundary=\"%s\"\r\n", boundary))
	b.WriteString("\r\n")

	// Text part
	textWriter, _ := writer.CreatePart(textproto.MIMEHeader{
		"Content-Type": {"text/plain; charset=\"utf-8\""},
	})
	textWriter.Write([]byte(body))

	// Attachment part
	contentType := "application/octet-stream"
	if ct := mime.TypeByExtension(fileName[strings.LastIndex(fileName, "."):]); ct != "" {
		contentType = ct
	}
	attachWriter, _ := writer.CreatePart(textproto.MIMEHeader{
		"Content-Type":              {contentType},
		"Content-Disposition":       {fmt.Sprintf("attachment; filename=\"%s\"", fileName)},
		"Content-Transfer-Encoding": {"base64"},
	})
	attachWriter.Write(fileData)

	writer.Close()
	return b.String()
}

func buildBulkMessage(subject, body string) string {
	var b strings.Builder
	b.WriteString(fmt.Sprintf("From: John Victor @ WaterParty <%s>\r\n", db.GmailAddr))
	b.WriteString(fmt.Sprintf("To: %s\r\n", db.GmailAddr))
	b.WriteString(fmt.Sprintf("Subject: %s\r\n", mime.QEncoding.Encode("utf-8", subject)))
	b.WriteString("MIME-Version: 1.0\r\n")
	b.WriteString("Content-Type: text/plain; charset=\"utf-8\"\r\n")
	b.WriteString("\r\n" + body)
	return b.String()
}

func sendViaSMTP(to, msg, password string) error {
	return smtpSend(to, msg, password)
}

func sendViaSMTPBCC(recipients []string, msg, password string) error {
	return smtpSendBCC(recipients, msg, password)
}

func smtpSend(to, msg, password string) error {
	host, port := db.SMTPServer, db.SMTPPort
	addr := fmt.Sprintf("%s:%d", host, port)

	client, err := smtp.Dial(addr)
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}
	defer client.Close()

	if err := client.StartTLS(&tls.Config{ServerName: host}); err != nil {
		return fmt.Errorf("starttls: %w", err)
	}

	auth := smtp.PlainAuth("", db.GmailAddr, password, host)
	if err := client.Auth(auth); err != nil {
		return fmt.Errorf("auth: %w", err)
	}

	if err := client.Mail(db.GmailAddr); err != nil {
		return fmt.Errorf("mail: %w", err)
	}
	if err := client.Rcpt(to); err != nil {
		return fmt.Errorf("rcpt: %w", err)
	}

	w, err := client.Data()
	if err != nil {
		return fmt.Errorf("data: %w", err)
	}
	w.Write([]byte(msg))
	w.Close()

	return nil
}

func smtpSendBCC(recipients []string, msg, password string) error {
	host, port := db.SMTPServer, db.SMTPPort
	addr := fmt.Sprintf("%s:%d", host, port)

	client, err := smtp.Dial(addr)
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}
	defer client.Close()

	if err := client.StartTLS(&tls.Config{ServerName: host}); err != nil {
		return fmt.Errorf("starttls: %w", err)
	}

	auth := smtp.PlainAuth("", db.GmailAddr, password, host)
	if err := client.Auth(auth); err != nil {
		return fmt.Errorf("auth: %w", err)
	}

	if err := client.Mail(db.GmailAddr); err != nil {
		return fmt.Errorf("mail: %w", err)
	}
	for _, r := range recipients {
		if err := client.Rcpt(r); err != nil {
			return fmt.Errorf("rcpt %s: %w", r, err)
		}
	}

	w, err := client.Data()
	if err != nil {
		return fmt.Errorf("data: %w", err)
	}
	w.Write([]byte(msg))
	w.Close()

	return nil
}
