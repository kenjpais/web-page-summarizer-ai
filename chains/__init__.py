"""
chains package

This package sets up and executes prompt-based workflows using LangChain's Runnable interface and a local LLM (Language Learning Model).
It dynamically loads prompt templates for text summarization, classification, and project-level summarization from environment-defined configuration files.
Prompts are parsed and formatted using LangChain's PromptTemplate, then executed via a local language model pipeline.
"""
