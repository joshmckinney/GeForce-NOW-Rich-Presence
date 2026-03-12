package metadata

import (
	"log"

	"github.com/joshmckinney/geforcenow-presence/internal/gog"
	"github.com/joshmckinney/geforcenow-presence/internal/steam"
)

// FetchArt tries to find a clear hero/box art image for the given game.
func FetchArt(gameName string) string {
	log.Printf("🔍 Searching for image metadata for game: %s", gameName)

	if imgURL, err := steam.FetchSteamArt(gameName); err == nil {
		log.Printf("🖼️ Found image on Steam: %s", imgURL)
		return imgURL
	} else {
		log.Printf("⚠️ Steam search failed: %v", err)
	}

	if imgURL, err := gog.FetchGOGArt(gameName); err == nil {
		log.Printf("🖼️ Found image on GOG: %s", imgURL)
		return imgURL
	} else {
		log.Printf("⚠️ GOG search failed: %v", err)
	}

	// Fallback to the generic "steam" or "geforce_now" asset bundle keys on Discord if available.
	log.Println("⚠️ All metadata API searches failed, using generic icon.")
	return "geforce_now"
}
