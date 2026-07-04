package handlers

import (
	"encoding/csv"
	"fmt"
	"math"
	"strings"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"counter-terrorism-initiative/internal/db"
	"counter-terrorism-initiative/internal/mail"
	"counter-terrorism-initiative/internal/models"
	"counter-terrorism-initiative/internal/social"
)

func GetStats(c *fiber.Ctx) error {
	stats, err := db.GetStats()
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}
	return c.JSON(stats)
}

func GetContacts(c *fiber.Ctx) error {
	f := db.ContactFilter{
		Search:   c.Query("search"),
		Vertical: c.Query("vertical"),
		Type:     c.Query("type"),
		Source:   c.Query("source"),
		SortBy:   c.Query("sort_by", "company"),
		SortDir:  c.Query("sort_dir", "asc"),
		Page:     c.QueryInt("page", 1),
		PerPage:  c.QueryInt("per_page", 50),
	}

	contacts, total, err := db.ListContacts(f)
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	totalPages := int(math.Max(1, float64((total+f.PerPage-1)/f.PerPage)))

	contactList := make([]models.Contact, len(contacts))
	for i, contact := range contacts {
		socialEntries := social.Parse(contact.Notes)
		contact.Social = socialEntries
		if len(contact.Notes) > 120 {
			contact.Notes = contact.Notes[:120] + "..."
		}
		contactList[i] = contact
	}

	return c.JSON(models.ContactsResponse{
		Contacts:   contactList,
		Total:      total,
		Page:       f.Page,
		PerPage:    f.PerPage,
		TotalPages: totalPages,
	})
}

func GetContact(c *fiber.Ctx) error {
	id := c.Params("id")
	contact, err := db.GetContact(id)
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}
	if contact == nil {
		return c.Status(404).JSON(fiber.Map{"error": "Not found"})
	}
	contact.Social = social.Parse(contact.Notes)
	return c.JSON(contact)
}

func GetFilters(c *fiber.Ctx) error {
	fr, err := db.GetFilters()
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}
	return c.JSON(fr)
}

func ExportCSV(c *fiber.Ctx) error {
	f := db.ContactFilter{
		Search:   c.Query("search"),
		Vertical: c.Query("vertical"),
		Type:     c.Query("type"),
		Source:   c.Query("source"),
		SortBy:   c.Query("sort_by", "company"),
		SortDir:  c.Query("sort_dir", "asc"),
	}

	contacts, err := db.ExportCSV(f)
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	var b strings.Builder
	writer := csv.NewWriter(&b)
	writer.Write([]string{"ID", "Company", "Contact Name", "Email", "Phone", "Website", "Type", "Vertical", "Source", "Status", "Notes", "Created At", "Updated At"})

	for _, contact := range contacts {
		writer.Write([]string{
			contact.ID, contact.Company, contact.ContactName, strings.Join(contact.Emails, ", "),
			contact.Phone, contact.Website, contact.Type, contact.Vertical,
			contact.Source, contact.Status, contact.Notes, contact.CreatedAt, contact.UpdatedAt,
		})
	}
	writer.Flush()

	filenameParts := []string{}
	if f.Search != "" {
		filenameParts = append(filenameParts, strings.ReplaceAll(f.Search, " ", "_"))
	}
	if f.Vertical != "" {
		filenameParts = append(filenameParts, strings.ReplaceAll(f.Vertical, " ", "_"))
	}
	if f.Type != "" {
		filenameParts = append(filenameParts, strings.ReplaceAll(f.Type, " ", "_"))
	}
	if f.Source != "" {
		filenameParts = append(filenameParts, strings.ReplaceAll(f.Source, " ", "_"))
	}

	filename := "contacts_all.csv"
	if len(filenameParts) > 0 {
		filename = "contacts_" + strings.Join(filenameParts, "_") + ".csv"
	}

	c.Set("Content-Type", "text/csv; charset=utf-8")
	c.Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, filename))
	c.Set("Content-Type", "text/csv; charset=utf-8-sig")
	return c.SendString("\ufeff" + b.String())
}

func ExportSelectedCSV(c *fiber.Ctx) error {
	var req models.ExportSelectedRequest
	if err := c.BodyParser(&req); err != nil || len(req.IDs) == 0 {
		return c.Status(400).JSON(fiber.Map{"error": "No contact IDs provided"})
	}

	contacts, err := db.ExportSelectedCSV(req.IDs)
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	var b strings.Builder
	writer := csv.NewWriter(&b)
	writer.Write([]string{"ID", "Company", "Contact Name", "Email", "Phone", "Website", "Type", "Vertical", "Source", "Status", "Notes", "Created At", "Updated At"})

	for _, contact := range contacts {
		writer.Write([]string{
			contact.ID, contact.Company, contact.ContactName, strings.Join(contact.Emails, ", "),
			contact.Phone, contact.Website, contact.Type, contact.Vertical,
			contact.Source, contact.Status, contact.Notes, contact.CreatedAt, contact.UpdatedAt,
		})
	}
	writer.Flush()

	filename := fmt.Sprintf("contacts_selected_%d.csv", len(req.IDs))

	c.Set("Content-Type", "text/csv; charset=utf-8")
	c.Set("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, filename))
	return c.SendString("\ufeff" + b.String())
}

func SendEmail(c *fiber.Ctx) error {
	// Accept both JSON and form-data (for file attachments)
	var contactID, subject, body, customEmail string
	var fileData []byte
	var fileName string

	contentType := string(c.Request().Header.ContentType())
	if strings.Contains(contentType, "application/json") {
		// JSON body (text-only emails from dashboard)
		var req models.SendEmailRequest
		if err := c.BodyParser(&req); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Request body required"})
		}
		contactID = req.ContactID
		subject = req.Subject
		body = req.Body
		customEmail = req.Email
	} else {
		// Form-data (with optional file attachment)
		contactID = c.FormValue("contact_id")
		subject = c.FormValue("subject")
		body = c.FormValue("body")
		customEmail = c.FormValue("email")

		file, err := c.FormFile("file")
		if err == nil && file != nil {
			f, err := file.Open()
			if err == nil {
				fileData = make([]byte, file.Size)
				f.Read(fileData)
				f.Close()
				fileName = file.Filename
			}
		}
	}

	if subject == "" || body == "" {
		return c.Status(400).JSON(fiber.Map{"error": "Subject and body are required"})
	}

	toEmail := customEmail
	if toEmail == "" && contactID != "" {
		email, _, err := db.GetContactEmail(contactID)
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": err.Error()})
		}
		if email == "" {
			return c.Status(404).JSON(fiber.Map{"error": "Contact not found"})
		}
		toEmail = email
	}
	if toEmail == "" {
		return c.Status(400).JSON(fiber.Map{"error": "No email address provided or found for this contact"})
	}

	result := mail.SendEmail(toEmail, subject, body, fileData, fileName)
	if !result.Success {
		return c.Status(500).JSON(fiber.Map{"error": result.Error})
	}

	go db.LogEmail(contactID, toEmail, subject, body, "sent", "")
	return c.JSON(result)
}

func GetEmailLog(c *fiber.Ctx) error {
	contactID := c.Query("contact_id")
	limit := c.QueryInt("limit", 50)

	logs, totalSent, err := db.GetEmailLog(contactID, limit)
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	return c.JSON(models.EmailLogResponse{
		Logs:      logs,
		TotalSent: totalSent,
	})
}

func SendBulkEmail(c *fiber.Ctx) error {
	var req models.SendBulkEmailRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(400).JSON(fiber.Map{"error": "Request body required"})
	}

	if len(req.Emails) == 0 {
		return c.Status(400).JSON(fiber.Map{"error": "At least one email is required"})
	}
	if req.Subject == "" || req.Body == "" {
		return c.Status(400).JSON(fiber.Map{"error": "Subject and body are required"})
	}

	sent, errMsg := mail.SendBulkEmail(req.Emails, req.Subject, req.Body)
	if errMsg != "" {
		return c.Status(500).JSON(fiber.Map{"error": errMsg})
	}

	go func() {
		for _, email := range req.Emails {
			db.LogEmail("", email, req.Subject, req.Body, "sent", "")
		}
	}()

	return c.JSON(fiber.Map{
		"success": true,
		"sent":    sent,
		"subject": req.Subject,
	})
}

func formatID() string {
	return uuid.New().String()
}
