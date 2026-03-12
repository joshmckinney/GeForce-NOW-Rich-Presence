package dbussvc

import (
	"fmt"
	"log"

	"github.com/godbus/dbus/v5"
	"github.com/godbus/dbus/v5/introspect"
)

const (
	serviceName = "com.github.joshmckinney.GFNPresence"
	objectPath  = "/com/github/joshmckinney/GFNPresence"
	interfaceID = "com.github.joshmckinney.GFNPresence.Control"
)

// GFNService is the DBus object.
type GFNService struct {
	overrideChan chan string
}

// ForceGame is called by the DBus client to force a game name.
func (s *GFNService) ForceGame(gameName string) *dbus.Error {
	log.Printf("📥 Received DBus override: %s", gameName)
	select {
	case s.overrideChan <- gameName:
	default:
	}
	return nil
}

// ClearOverride is called by the DBus client to stop forcing a game.
func (s *GFNService) ClearOverride() *dbus.Error {
	log.Println("📥 Cleared DBus override. Returning to auto-detection.")
	select {
	case s.overrideChan <- "":
	default:
	}
	return nil
}

// StartDBusService connects to the session bus, exports the service, and returns a channel of override strings.
func StartDBusService() (<-chan string, error) {
	conn, err := dbus.ConnectSessionBus()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to session bus: %w", err)
	}

	overrideChan := make(chan string, 1) // buffered to avoid blocking D-Bus
	service := &GFNService{overrideChan: overrideChan}

	err = conn.Export(service, objectPath, interfaceID)
	if err != nil {
		return nil, fmt.Errorf("failed to export DBus service: %w", err)
	}

	// Export standard DBus introspection data
	n := &introspect.Node{
		Name: objectPath,
		Interfaces: []introspect.Interface{
			introspect.IntrospectData,
			{
				Name: interfaceID,
				Methods: []introspect.Method{
					{
						Name: "ForceGame",
						Args: []introspect.Arg{
							{Name: "gameName", Type: "s", Direction: "in"},
						},
					},
					{
						Name: "ClearOverride",
					},
				},
			},
		},
	}
	err = conn.Export(introspect.NewIntrospectable(n), objectPath, "org.freedesktop.DBus.Introspectable")
	if err != nil {
		return nil, fmt.Errorf("failed to export introspect: %w", err)
	}

	reply, err := conn.RequestName(serviceName, dbus.NameFlagDoNotQueue)
	if err != nil {
		return nil, fmt.Errorf("failed to request name: %w", err)
	}
	if reply != dbus.RequestNameReplyPrimaryOwner {
		return nil, fmt.Errorf("name already taken")
	}

	log.Printf("🔌 DBus service listening at %s", serviceName)
	return overrideChan, nil
}
