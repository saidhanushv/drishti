import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { LlmParserService } from './services/llm-parser.service';

interface ChatMessage {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe, RouterModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {

  @ViewChild('chatBody', { static: false }) chatBody!: ElementRef;

  // Chat variables
  messages: ChatMessage[] = [];
  userMessage = '';
  isLoading = false;
  isChatOpen = false;
  currentStatus = '';
  streamingMessage = '';

  // Backend API
  private apiUrl = '/query';
  private streamUrl = '/query/stream';

  constructor(
    private http: HttpClient,
    private router: Router,
    private llmParser: LlmParserService
  ) { }

  ngOnInit(): void {
    this.addWelcomeMessage();
  }

  toggleChat() {
    this.isChatOpen = !this.isChatOpen;
  }

  addWelcomeMessage() {
    this.messages.push({
      text: "Hi! I'm Drishti, your analytics assistant. Ask me anything about the dashboard!",
      isUser: false,
      timestamp: new Date()
    });
  }

  async sendMessage() {
    if (!this.userMessage.trim() || this.isLoading) return;

    const messageText = this.userMessage.trim();
    this.messages.push({
      text: messageText,
      isUser: true,
      timestamp: new Date()
    });

    this.userMessage = '';
    this.isLoading = true;
    this.currentStatus = '';
    this.streamingMessage = '';
    this.scrollToBottom();

    // Track navigation info to prepend to response
    let navigationPrefix = '';

    // Parse query for navigation and filtering
    try {
      const navigationInstruction = this.llmParser.parseQuery(messageText);

      if (navigationInstruction && navigationInstruction.targetPage) {
        await this.llmParser.applyNavigationInstruction(navigationInstruction);

        const filterInfo = this.getFilterInfo(navigationInstruction);
        navigationPrefix = `📍 Navigated to ${navigationInstruction.targetPage} page${filterInfo}\n\n`;
      }
    } catch (error) {
      console.error('Error parsing query for navigation:', error);
    }

    try {
      // Use streaming endpoint for answer
      await this.streamResponse(messageText, navigationPrefix);
    } catch (err) {
      this.messages.push({
        text:
          '⚠️ Unable to reach backend. Please check your connection.',
        isUser: false,
        timestamp: new Date()
      });
      this.isLoading = false;
      this.currentStatus = '';
      this.streamingMessage = '';
    }

    this.scrollToBottom();
  }

  private getFilterInfo(instruction: any): string {
    const filters: string[] = [];
    if (instruction.filters.year) filters.push(`Year: ${instruction.filters.year}`);
    if (instruction.filters.region && instruction.filters.region.length > 0) {
      filters.push(`Region: ${instruction.filters.region.join(', ')}`);
    }
    if (instruction.filters.ragStatus && instruction.filters.ragStatus.length > 0) {
      filters.push(`RAG: ${instruction.filters.ragStatus.join(', ')}`);
    }
    if (instruction.filters.halfYear) filters.push(`Half Year: ${instruction.filters.halfYear}`);

    return filters.length > 0 ? ` with filters: ${filters.join(', ')}` : '';
  }

  async streamResponse(question: string, navigationPrefix: string = '') {
    const response = await fetch(this.streamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question })
    });

    if (!response.ok) {
      throw new Error('Stream request failed');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    if (!reader) {
      throw new Error('No reader available');
    }

    // Create a placeholder message for streaming
    const streamMessageIndex = this.messages.length;
    this.messages.push({
      text: navigationPrefix, // Start with navigation prefix if present
      isUser: false,
      timestamp: new Date()
    });

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));

            if (data.type === 'status') {
              this.currentStatus = data.message;
              this.scrollToBottom();
            } else if (data.type === 'content') {
              this.streamingMessage += data.content;
              this.messages[streamMessageIndex].text = navigationPrefix + this.streamingMessage;
              this.scrollToBottom();
            } else if (data.type === 'done') {
              if (data.content && !this.streamingMessage) {
                this.messages[streamMessageIndex].text = navigationPrefix + data.content;
              }
              this.isLoading = false;
              this.currentStatus = '';
              this.streamingMessage = '';
              this.scrollToBottom();
              return;
            } else if (data.type === 'error') {
              this.messages[streamMessageIndex].text = navigationPrefix + `Error: ${data.message}`;
              this.isLoading = false;
              this.currentStatus = '';
              this.streamingMessage = '';
              this.scrollToBottom();
              return;
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
    }

    this.isLoading = false;
    this.currentStatus = '';
    this.streamingMessage = '';
  }

  handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  scrollToBottom() {
    setTimeout(() => {
      if (this.chatBody) {
        this.chatBody.nativeElement.scrollTop =
          this.chatBody.nativeElement.scrollHeight;
      }
    }, 100);
  }

  formatMessage(text: string): string {
    return text.replace(/\n/g, '<br>').replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
  }
}