package updater

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

const (
	latestReleaseURL = "https://api.github.com/repos/joshmckinney/geforcenow-presence/releases/latest"
	releasesPageURL  = "https://github.com/joshmckinney/geforcenow-presence/releases"
)

type githubRelease struct {
	TagName string `json:"tag_name"`
}

// CheckForUpdate queries GitHub for the latest release tag and compares it to currentVersion.
// It returns the new version string if an update is available, otherwise empty string.
func CheckForUpdate(currentVersion string) (string, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(latestReleaseURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var release githubRelease
	if err := json.NewDecoder(resp.Body).Decode(&release); err != nil {
		return "", err
	}

	latest := strings.TrimPrefix(release.TagName, "v")
	current := strings.TrimPrefix(currentVersion, "v")

	if isNewer(current, latest) {
		return release.TagName, nil
	}

	return "", nil
}

// isNewer is a simple version comparator (v0.1.0-beta etc)
func isNewer(current, latest string) bool {
	if latest == "" || latest == current {
		return false
	}
	// Simple string comparison for now as we follow semver-ish tags
	// In a beta phase, even simple string diff usually suffices if we always increment
	return latest > current
}

func GetReleasesURL() string {
	return releasesPageURL
}
