<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue';
import { ElMessage } from 'element-plus';
import { UserFilled, ArrowUp } from '@element-plus/icons-vue';
import WebShell from '@/components/WebShell.vue';
import { sendChatMessage, createChatWebSocket, type ChatMessage } from '@/api/chat';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();

const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '你好！我是你的 AI 健身助手 💪\n\n我可以帮你：\n• 解答健身动作相关问题\n• 分析训练中的错误姿势\n• 提供训练建议和恢复指导\n• 制定个性化训练计划\n\n有什么我可以帮你的吗？',
    timestamp: Date.now(),
  },
]);
const inputMessage = ref('');
const loading = ref(false);
const sessionId = ref(`chat_${Date.now()}`);
const messagesContainer = ref<HTMLElement | null>(null);
const useWebSocket = ref(false);
let ws: WebSocket | null = null;
let pendingResolve: (() => void) | null = null;
let pendingReject: ((err: any) => void) | null = null;

// Quick suggestion buttons
const suggestions = [
  '深蹲时膝盖内扣怎么办？',
  '新手如何制定训练计划？',
  '训练后如何恢复？',
  '如何判断深蹲深度是否够？',
];

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}

async function sendMessage() {
  const content = inputMessage.value.trim();
  if (!content || loading.value) return;

  // Add user message
  messages.value.push({
    role: 'user',
    content,
    timestamp: Date.now(),
  });
  inputMessage.value = '';
  scrollToBottom();

  loading.value = true;

  try {
    if (useWebSocket.value) {
      await sendWebSocketMessage(content);
    } else {
      await sendHttpMessage(content);
    }
  } catch (error: any) {
    console.error('Failed to send message:', error);
    const detail = error?.response?.data?.detail || error?.message || '请稍后重试';
    ElMessage.error(`发送失败：${detail}`);
    messages.value.push({
      role: 'assistant',
      content: `抱歉，这次没有拿到 AI 回复。\n\n原因：${detail}`,
      timestamp: Date.now(),
    });
  } finally {
    loading.value = false;
    scrollToBottom();
  }
}

async function sendHttpMessage(content: string) {
  const { data } = await sendChatMessage({
    message: content,
    session_id: sessionId.value,
  });
  
  messages.value.push({
    role: 'assistant',
    content: data.response,
    timestamp: Date.now(),
  });
  
  sessionId.value = data.session_id;
}

async function sendWebSocketMessage(content: string) {
  return new Promise<void>((resolve, reject) => {
    pendingResolve = resolve;
    pendingReject = reject;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      const token = authStore.token || '';
      ws = createChatWebSocket(sessionId.value, token);

      let responseContent = '';

      ws.onopen = () => {
        ws?.send(JSON.stringify({ message: content }));
      };

      ws.onmessage = (event) => {
        handleWsMessage(event, responseContent, (updated) => { responseContent = updated; });
      };

      ws.onerror = (error) => {
        pendingReject?.(error);
        pendingReject = null;
        pendingResolve = null;
      };

      ws.onclose = () => {
        // If still pending when socket closes, reject
        if (pendingReject) {
          pendingReject(new Error('连接已断开'));
          pendingReject = null;
          pendingResolve = null;
        }
        ws = null;
      };
    } else {
      ws.send(JSON.stringify({ message: content }));
    }
  });
}

function handleWsMessage(event: MessageEvent, content: string, updateContent: (v: string) => void) {
  let localContent = content;
  try {
    const data = JSON.parse(event.data);
    if (data.type === 'content') {
      localContent += data.content;
      updateContent(localContent);
      const lastMsg = messages.value[messages.value.length - 1];
      if (lastMsg.role === 'assistant' && !data.is_end) {
        lastMsg.content = localContent;
      } else if (lastMsg.role !== 'assistant' && !data.is_end) {
        messages.value.push({
          role: 'assistant',
          content: localContent,
          timestamp: Date.now(),
        });
      }
      if (data.is_end) {
        // Ensure final content is set
        const finalMsg = messages.value[messages.value.length - 1];
        if (finalMsg.role === 'assistant') {
          finalMsg.content = localContent;
        }
        pendingResolve?.();
        pendingResolve = null;
        pendingReject = null;
      }
      scrollToBottom();
    } else if (data.type === 'error') {
      pendingReject?.(new Error(data.content));
      pendingReject = null;
      pendingResolve = null;
    }
  } catch {
    // Plain text message fallback
    localContent += event.data;
    updateContent(localContent);
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg.role === 'assistant') {
      lastMsg.content = localContent;
    } else {
      messages.value.push({
        role: 'assistant',
        content: localContent,
        timestamp: Date.now(),
      });
    }
    scrollToBottom();
  }
}

function useSuggestion(text: string) {
  inputMessage.value = text;
  sendMessage();
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

onBeforeUnmount(() => {
  if (ws) {
    ws.close();
    ws = null;
  }
});

onMounted(() => {
  scrollToBottom();
});
</script>

<template>
  <WebShell title="AI 助手" subtitle="你的专属健身顾问，随时解答训练问题">
    <div class="mx-auto flex h-[calc(100vh-240px)] max-w-4xl flex-col gap-4 lg:h-[calc(100vh-200px)]">
      <!-- Chat Messages -->
      <div 
        ref="messagesContainer"
        class="app-card flex-1 overflow-y-auto p-4 scrollbar-thin"
      >
        <div class="space-y-4">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex gap-3"
            :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
          >
            <!-- Avatar -->
            <div
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm"
              :class="msg.role === 'user' 
                ? 'bg-gradient-to-br from-indigo to-ocean text-white' 
                : 'bg-gradient-to-br from-orange to-coral text-white'"
            >
              <el-icon v-if="msg.role === 'user'"><UserFilled /></el-icon>
              <span v-else>🤖</span>
            </div>
            
            <!-- Message Bubble -->
            <div
              class="max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-line"
              :class="msg.role === 'user'
                ? 'bg-indigo text-white rounded-tr-sm'
                : 'bg-canvas text-ink rounded-tl-sm'"
            >
              {{ msg.content }}
            </div>
          </div>
          
          <!-- Loading Indicator -->
          <div v-if="loading" class="flex gap-3">
            <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-orange to-coral text-sm text-white">
              <span>🤖</span>
            </div>
            <div class="flex items-center gap-1 rounded-2xl rounded-tl-sm bg-canvas px-4 py-3">
              <div class="h-2 w-2 animate-bounce rounded-full bg-muted" style="animation-delay: 0s" />
              <div class="h-2 w-2 animate-bounce rounded-full bg-muted" style="animation-delay: 0.2s" />
              <div class="h-2 w-2 animate-bounce rounded-full bg-muted" style="animation-delay: 0.4s" />
            </div>
          </div>
        </div>
      </div>

      <!-- Suggestions -->
      <div v-if="messages.length <= 1" class="flex flex-wrap gap-2">
        <button
          v-for="suggestion in suggestions"
          :key="suggestion"
          class="rounded-full bg-white px-4 py-2 text-xs text-muted shadow-sm transition hover:bg-indigo/5 hover:text-indigo border border-black/5"
          @click="useSuggestion(suggestion)"
        >
          {{ suggestion }}
        </button>
      </div>

      <!-- Input Area -->
      <div class="app-card p-3">
        <div class="flex items-end gap-2">
          <textarea
            v-model="inputMessage"
            rows="1"
            placeholder="输入你的问题...（按 Enter 发送，Shift+Enter 换行）"
            class="max-h-32 min-h-[44px] flex-1 resize-none rounded-xl bg-canvas px-4 py-3 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-indigo/20"
            @keydown="handleKeydown"
          />
          <el-button
            type="primary"
            circle
            class="!h-11 !w-11 !bg-indigo !border-none"
            :loading="loading"
            :disabled="!inputMessage.trim()"
            @click="sendMessage"
          >
            <el-icon><ArrowUp /></el-icon>
          </el-button>
        </div>
        <div class="mt-2 flex items-center justify-between px-1">
          <p class="text-[10px] text-muted">
            AI 助手提供的信息仅供参考，具体训练请根据个人情况调整
          </p>
          <el-switch
            v-model="useWebSocket"
            size="small"
            active-text="流式响应"
            class="!text-[10px]"
          />
        </div>
      </div>
    </div>
  </WebShell>
</template>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 4px;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: rgba(0,0,0,0.2);
}
</style>
