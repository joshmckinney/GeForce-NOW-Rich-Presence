package steam

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"time"
)

var client = &http.Client{Timeout: 10 * time.Second}

type SteamSearchResponse struct {
	Total int `json:"total"`
	Items []struct {
		ID int `json:"id"`
	} `json:"items"`
}

func FetchSteamArt(gameName string) (string, error) {
	encodedName := url.QueryEscape(gameName)
	searchURL := fmt.Sprintf("https://store.steampowered.com/api/storesearch/?term=%s&l=english&cc=US", encodedName)

	resp, err := client.Get(searchURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result SteamSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil || result.Total == 0 {
		return "", fmt.Errorf("game not found on Steam")
	}

	if len(result.Items) == 0 {
		return "", fmt.Errorf("game not found on Steam")
	}

	return fmt.Sprintf("https://cdn.akamai.steamstatic.com/steam/apps/%d/header.jpg", result.Items[0].ID), nil
}
