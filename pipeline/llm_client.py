"""
LLM Client — Groq API Wrapper
===============================
Uses the Groq Python SDK for ultra-fast inference with
open-source models like Llama 4 Maverick.

Groq provides free-tier access with generous rate limits
and blazing-fast inference on their LPU hardware.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Thin wrapper over Groq API for text generation."""

    def __init__(self, model_id: str = None, temperature: float = None, max_tokens: int = None):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found in environment. "
                "Copy .env.example to .env and add your Groq API key."
            )

        self.model_id = model_id or os.getenv("MODEL_ID", "meta-llama/llama-4-maverick-17b-128e-instruct")
        self.temperature = temperature or float(os.getenv("TEMPERATURE", "0.8"))
        self.max_tokens = max_tokens or int(os.getenv("MAX_NEW_TOKENS", "2048"))

        self.client = Groq(api_key=api_key)
        print(f"[LLM] Initialized with model: {self.model_id}")
        print(f"[LLM] Using Groq API")

    def generate(self, prompt: str, system_message: str = None, temperature: float = None) -> str:
        """
        Generate text using Groq's chat completions API.

        Args:
            prompt: The user prompt / instruction
            system_message: Optional system-level instruction
            temperature: Override default temperature for this call

        Returns:
            Generated text string
        """
        temp = temperature or self.temperature
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        # Use non-streaming for simplicity in pipeline
        completion = self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            max_completion_tokens=self.max_tokens,
            temperature=temp,
            top_p=1,
            stream=False,
        )

        return completion.choices[0].message.content.strip()

    def generate_long(self, prompt: str, system_message: str = None, max_tokens: int = 4096) -> str:
        """
        Generate longer content (for story generation stage).
        Temporarily overrides max_tokens for this call.
        """
        original_max = self.max_tokens
        self.max_tokens = max_tokens
        try:
            result = self.generate(prompt, system_message)
        finally:
            self.max_tokens = original_max
        return result
