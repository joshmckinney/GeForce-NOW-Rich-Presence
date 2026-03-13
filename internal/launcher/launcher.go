package launcher

import (
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const gfnFlatpakID = "com.nvidia.geforcenow"

func IsProcessRunning(nameSubstr string) bool {
	entries, err := os.ReadDir("/proc")
	if err != nil {
		return false
	}

	nameL := strings.ToLower(nameSubstr)

	for _, entry := range entries {
		if !entry.IsDir() || entry.Name()[0] < '0' || entry.Name()[0] > '9' {
			continue
		}

		cmdline, err := os.ReadFile(filepath.Join("/proc", entry.Name(), "cmdline"))
		if err != nil {
			continue
		}

		parts := strings.Split(string(cmdline), "\x00")
		if len(parts) == 0 || parts[0] == "" {
			continue
		}

		exeBase := strings.ToLower(filepath.Base(parts[0]))
		cmdlineStr := strings.ToLower(string(cmdline))

		// Strict match on the binary name or generic substring match for flatpaks
		matches := strings.Contains(exeBase, nameL) || (nameL == "geforcenow" && strings.Contains(cmdlineStr, "com.nvidia.geforcenow"))

		if matches &&
			!strings.Contains(cmdlineStr, "geforcenow-presence") &&
			!strings.Contains(cmdlineStr, "geforcenow-presence-dummies") {
			return true
		}
	}
	return false
}

// LaunchGFN starts the GeForce NOW Electron Flatpak.
func LaunchGFN() bool {
	if IsProcessRunning("GeForceNOW") {
		log.Println("💡 GeForce NOW is already running (launch skipped)")
		return true
	}

	log.Println("🚀 Launching GeForce NOW Flatpak...")
	cmd := exec.Command("flatpak", "run", gfnFlatpakID)
	if err := cmd.Start(); err != nil {
		log.Printf("❌ Failed to launch GeForce NOW: %v", err)
		return false
	}
	return true
}

// LaunchDiscord starts Discord.
func LaunchDiscord() bool {
	if IsProcessRunning("Discord") {
		log.Println("💡 Discord is already running (launch skipped)")
		return true
	}

	// Try common Discord binary locations
	discordPaths := []string{
		"/usr/bin/Discord",
		"/usr/bin/discord",
		"/usr/local/bin/discord",
	}

	for _, p := range discordPaths {
		if _, err := os.Stat(p); err == nil {
			log.Println("🚀 Launching Discord...")
			cmd := exec.Command(p)
			if err := cmd.Start(); err != nil {
				log.Printf("❌ Failed to launch Discord: %v", err)
				return false
			}
			return true
		}
	}

	// Try flatpak Discord
	cmd := exec.Command("flatpak", "run", "com.discordapp.Discord")
	if err := cmd.Start(); err != nil {
		log.Println("⚠️ Discord not found in standard locations or Flatpak")
		return false
	}
	return true
}
