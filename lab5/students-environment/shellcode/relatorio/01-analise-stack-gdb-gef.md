# Relatório — Lab 5 (MC833): Buffer Overflow e Injeção de Shellcode

## Análise da pilha com GDB/GEF

### Objetivo

Antes de escrever o exploit, o binário vulnerável (`alvo_vulneravel/server.c`) foi
analisado ao vivo com GDB + GEF (plugin que expõe o estado da pilha, registradores e
memória em cada instrução), para confirmar experimentalmente onde o `strcpy`
vulnerável escreve em relação ao *saved RBP* e ao endereço de retorno.

### O código vulnerável

```c
void bof(char *str) {
    char buffer[50];
    printf("[INFO LEAK] O endereco real do buffer eh: %p\n", (void *)buffer);
    fflush(stdout);
    strcpy(buffer, str);          // <-- sem checagem de limite
    printf("Mensagem copiada!\n");
}

int main() {
    char input[500];
    read(STDIN_FILENO, input, 500);
    if (read(...) > 0) bof(input);
}
```

`buffer` tem 50 bytes, mas `strcpy(buffer, str)` copia `str` inteiro, sem nunca
verificar o tamanho de `str` contra os 50 bytes disponíveis. Como `str` vem
diretamente de `input`, que por sua vez foi lido do socket com `read(..., 500)`,
um atacante controla até 500 bytes que serão despejados a partir de `buffer` — bem
mais do que o espaço reservado para ele na pilha.

### Layout do frame de `bof` (confirmado via `disassemble` + GDB ao vivo)

```
        endereços crescentes →
 rbp-0x40 ┌───────────────────────────┐
          │   buffer[0..49]           │  50 bytes — onde o strcpy DEVERIA parar
 rbp-0x0e ├───────────────────────────┤
          │   padding/alinhamento     │  14 bytes de "sobra" do frame
 rbp+0x00 ├───────────────────────────┤
          │   saved RBP               │  8 bytes — rbp do caller (main)
 rbp+0x08 ├───────────────────────────┤
          │   saved return address    │  8 bytes — para onde o `ret` de bof volta
          └───────────────────────────┘
```

Como o `strcpy` escreve de forma contígua a partir de `buffer[0]` (endereços
crescentes), um payload grande o suficiente atravessa o padding, sobrescreve o
*saved RBP* e, na sequência, o **endereço de retorno** — que é exatamente o alvo
do ataque, pois é o valor que o `ret` final de `bof` usa para decidir para onde o
fluxo de execução volta.

Cálculo confirmado: **offset até o endereço de retorno = 0x48 = 72 bytes** a
partir do início de `buffer`. Ou seja, os 72 primeiros bytes do payload podem ser
qualquer coisa (foram usados como *NOP sled*/preenchimento), e os 8 bytes
seguintes (posições 72–79) caem exatamente sobre o endereço de retorno salvo na
pilha.

### Confirmação experimental (payloads de teste)

Para validar o cálculo estático, três payloads foram enviados ao binário dentro
do GDB, parando a execução imediatamente antes e depois do `call strcpy` para
comparar o estado da pilha:

| Payload | Conteúdo | Tamanho | Efeito esperado/observado |
|---|---|---|---|
| 1 | `"AAAABBBBCCCCDDDDEEEE\0"` | 21 bytes | Bem menor que os 50 bytes do `buffer` — não toca padding, RBP ou retorno. |
| 2 | 49×`'X'` + `\0` | 50 bytes | Preenche `buffer` exatamente até a borda, sem sobrar para o padding/RBP. |
| 3 | 8 bytes cada de `A,B,C,D,E,F,G,H,I,J` + `\0` | 81 bytes | Desenhado para alinhar com o layout acima: blocos A–H cobrem `buffer`+padding; **I** cai em cima do *saved RBP*; **J** cai em cima do **endereço de retorno**, sobrescrevendo-o com `0x4a4a4a4a4a4a4a4a` (bytes `J`) — valor inválido como endereço, causando *segfault* no `retq` final de `bof`. |

Essa progressão (1 → 2 → 3) mostra visualmente, byte a byte, o momento exato em
que o overflow deixa de ser inofensivo e passa a corromper dados de controle do
frame — o que é a essência do bug de buffer overflow: o programa nunca distingue
"dados do usuário" de "metadados de controle de fluxo" na pilha, e ambos convivem
na mesma região de memória contígua.

![Pilha logo após o `call strcpy` com o payload 3, GDB/GEF](img/stack-payload3-pos-strcpy.png)

*Estado da pilha (GDB/GEF) imediatamente após o `strcpy` retornar, com o payload 3.
`$rbp+0x00` (saved RBP) contém `0x4949494949494949` (bytes `I`) e `$rbp+0x08`
(endereço de retorno) contém `0x4a4a4a4a4a4a4a4a` (bytes `J`) — confirmando ao vivo
que o offset de 72 bytes calculado estaticamente é exatamente onde o controle de
fluxo do frame começa a ser sobrescrito.*

### Do overflow controlado ao RCE

Uma vez confirmado que os bytes 72–79 do payload controlam o endereço de retorno,
o exploit substitui o valor de teste (`J`×8) pelo endereço real de `buffer`
(obtido via o *info leak* que o próprio `server.c` imprime: `%p` do buffer) somado
a um deslocamento fixo (`INPUT_OFFSET_FROM_BUFFER = 0x50`) para apontar dentro de
`input`, onde o shellcode dinâmico foi colocado à frente de um *NOP sled*. Assim,
ao executar `ret`, o fluxo salta para dentro da própria pilha e executa o
shellcode injetado, obtendo execução arbitrária de código (RCE).
