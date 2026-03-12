package main

import "testing"

func TestVersion(t *testing.T) {
	expected := "0.1.0-beta"
	if version != expected {
		t.Errorf("Expected version %s, got %s", expected, version)
	}
}
