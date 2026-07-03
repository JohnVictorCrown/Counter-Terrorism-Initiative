package main

import (
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/template/html/v2"

	"counter-terrorism-initiative/internal/handlers"
)

func main() {
	engine := html.New(filepath.Join(".", "templates"), ".html")
	engine.AddFunc("default", func(s, d string) string {
		if s == "" {
			return d
		}
		return s
	})
	engine.AddFunc("truncate", func(s string, max int) string {
		if len(s) <= max {
			return s
		}
		return s[:max]
	})

	app := fiber.New(fiber.Config{
		Views: engine,
	})
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowHeaders: "Content-Type, Accept",
	}))
	app.Use(logger.New())

	// Static files
	app.Static("/static", "./static")

	// SPA root page
	app.Get("/", handlers.Index)

	// API routes
	api := app.Group("/api")
	api.Get("/stats", handlers.GetStats)
	api.Get("/contacts", handlers.GetContacts)
	api.Get("/contacts/:id", handlers.GetContact)
	api.Get("/filters", handlers.GetFilters)
	api.Get("/export-csv", handlers.ExportCSV)
	api.Post("/export-selected-csv", handlers.ExportSelectedCSV)
	api.Post("/send-email", handlers.SendEmail)
	api.Post("/send-bulk-email", handlers.SendBulkEmail)
	api.Get("/email-log", handlers.GetEmailLog)

	// Pages
	app.Get("/report", handlers.GetReport)

	app.Listen(":5000")
}
