package social

import (
	"regexp"
	"strings"

	"counter-terrorism-initiative/internal/models"
)

var socialPlatforms = map[string]struct {
	Name string
	Icon string
	URL  string
}{
	"x/twitter":  {"X", "𝕏", "https://x.com/"},
	"twitter":    {"Twitter", "𝕏", "https://x.com/"},
	"x":          {"X", "𝕏", "https://x.com/"},
	"instagram":  {"Instagram", "📷", "https://instagram.com/"},
	"facebook":   {"Facebook", "📘", "https://facebook.com/"},
	"youtube":    {"YouTube", "▶️", "https://youtube.com/"},
	"linkedin":   {"LinkedIn", "💼", "https://linkedin.com/company/"},
	"tiktok":     {"TikTok", "🎵", "https://tiktok.com/@"},
	"telegram":   {"Telegram", "✈️", "https://t.me/"},
	"whatsapp":   {"WhatsApp", "💬", "https://wa.me/"},
}

var socialPattern = regexp.MustCompile(`([A-Za-z][A-Za-z/]+)\s*(?::\s*)?@?([A-Za-z0-9][A-Za-z0-9_.\-@/]+)`)

var noSocialPattern = regexp.MustCompile(`\b(no|none|not|n't)\b`)

var periodSplit = regexp.MustCompile(`\.\s+`)

var commonWords = map[string]bool{
	"the": true, "and": true, "for": true, "are": true, "via": true, "using": true,
}

func Parse(notes string) []models.SocialEntry {
	if notes == "" || !strings.Contains(notes, "Social:") {
		return nil
	}

	idx := strings.Index(notes, "Social:")
	socialText := notes[idx+7:]

	for _, sep := range []string{"\n\n", "  \n", "\n- ", "\n* "} {
		if i := strings.Index(socialText, sep); i >= 0 {
			socialText = socialText[:i]
			break
		}
	}

	parts := periodSplit.Split(socialText, 2)
	socialText = strings.TrimSpace(parts[0])

	checkText := socialText
	if len(checkText) > 60 {
		checkText = checkText[:60]
	}
	if noSocialPattern.MatchString(strings.ToLower(checkText)) {
		return nil
	}

	matches := socialPattern.FindAllStringSubmatch(notes, -1)
	if len(matches) == 0 {
		matches = socialPattern.FindAllStringSubmatch(socialText, -1)
	}

	var results []models.SocialEntry
	for _, m := range matches {
		platformRaw := strings.TrimSpace(strings.ToLower(m[1]))
		handle := strings.TrimLeft(strings.TrimSpace(m[2]), "@")

		if len(handle) < 2 || commonWords[handle] {
			continue
		}

		matched := false
		for key, info := range socialPlatforms {
			keyParts := strings.Split(key, "/")
			for _, kp := range keyParts {
				if strings.Contains(platformRaw, kp) || strings.Contains(kp, platformRaw) {
					fullURL := info.URL + handle
					if key == "youtube" && !strings.HasPrefix(handle, "@") {
						fullURL = info.URL + "@" + handle
					}
					results = append(results, models.SocialEntry{
						Platform: info.Name,
						Icon:     info.Icon,
						Handle:   handle,
						URL:      fullURL,
					})
					matched = true
					break
				}
			}
			if matched {
				break
			}
		}

		if !matched && strings.HasPrefix(handle, "http") {
			results = append(results, models.SocialEntry{
				Platform: platformRaw,
				Icon:     "🔗",
				Handle:   handle,
				URL:      handle,
			})
		}
	}

	return results
}
