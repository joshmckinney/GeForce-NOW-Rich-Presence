package gog

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

var client = &http.Client{Timeout: 10 * time.Second}

type GOGSearchResponse struct {
	Products []struct {
		Image string `json:"image"`
	} `json:"products"`
}

func FetchGOGArt(gameName string) (string, error) {
	encodedName := url.QueryEscape(gameName)
	searchURL := fmt.Sprintf("https://embed.gog.com/games/ajax/filtered?mediaType=game&search=%s", encodedName)

	resp, err := client.Get(searchURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result GOGSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil || len(result.Products) == 0 {
		return "", fmt.Errorf("game not found on GOG")
	}

	imageURL := result.Products[0].Image
	if strings.HasPrefix(imageURL, "//") {
		imageURL = "https:" + imageURL
	}
	return imageURL + "_glx_master_256.jpg", nil
}
