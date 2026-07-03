package handlers

import (
	"time"

	"github.com/gofiber/fiber/v2"

	"counter-terrorism-initiative/internal/db"
	"counter-terrorism-initiative/internal/models"
)

func Index(c *fiber.Ctx) error {
	return c.SendFile("./templates/index.html")
}

func GetReport(c *fiber.Ctx) error {
	f := db.ContactFilter{
		Search:   c.Query("search"),
		Vertical: c.Query("vertical"),
		Type:     c.Query("type"),
		Source:   c.Query("source"),
	}

	rd, err := db.GetReportData(f)
	if err != nil {
		return c.Status(500).JSON(fiber.Map{"error": err.Error()})
	}

	rd.GeneratedAt = time.Now().Format("January 02, 2006 at 15:04")

	shortContacts := make([]models.Contact, len(rd.Contacts))
	for i, contact := range rd.Contacts {
		if len(contact.Notes) > 300 {
			contact.Notes = contact.Notes[:300] + "..."
		}
		shortContacts[i] = contact
	}
	rd.Contacts = shortContacts

	return c.Render("report", rd)
}
