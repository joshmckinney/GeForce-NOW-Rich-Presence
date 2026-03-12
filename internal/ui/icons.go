package ui

import (
	"bytes"
	"image"
	"image/color"
	"image/png"
)

var (
	iconGreen  []byte
	iconYellow []byte
	iconRed    []byte
)

func init() {
	iconGreen = generateCircleIcon(color.RGBA{R: 46, G: 204, B: 113, A: 255})
	iconYellow = generateCircleIcon(color.RGBA{R: 241, G: 196, B: 15, A: 255})
	iconRed = generateCircleIcon(color.RGBA{R: 231, G: 76, B: 60, A: 255})
}

func generateCircleIcon(c color.Color) []byte {
	size := 64
	radius := 28
	center := size / 2

	img := image.NewRGBA(image.Rect(0, 0, size, size))

	// Draw transparent background is default
	// Draw circle
	for y := 0; y < size; y++ {
		for x := 0; x < size; x++ {
			dx := x - center
			dy := y - center
			if dx*dx+dy*dy <= radius*radius {
				img.Set(x, y, c)
			}
		}
	}

	var buf bytes.Buffer
	png.Encode(&buf, img)
	return buf.Bytes()
}
