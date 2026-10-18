package main

import (
	"fmt"

	"github.com/golang-jwt/jwt/v4"
)

func main() {
	tok, err := jwt.Parse("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.x", func(t *jwt.Token) (any, error) {
		return []byte("s"), nil
	})
	if err != nil {
		fmt.Println(err)
		return
	}
	fmt.Println(tok.Valid)
}
