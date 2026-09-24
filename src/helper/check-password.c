/* Verify the invoking user's password through the system PAM stack. */
#include <security/pam_appl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int password_conversation(int count, const struct pam_message **messages,
                                 struct pam_response **result, void *context) {
    const char *password = context;
    struct pam_response *responses = calloc((size_t)count, sizeof(*responses));
    if (!responses) return PAM_BUF_ERR;
    for (int i = 0; i < count; ++i) {
        if (messages[i]->msg_style == PAM_PROMPT_ECHO_OFF) {
            responses[i].resp = strdup(password);
            if (responses[i].resp) continue;
        } else if (messages[i]->msg_style == PAM_TEXT_INFO ||
                   messages[i]->msg_style == PAM_ERROR_MSG) {
            continue;
        }
        for (int j = 0; j <= i; ++j) free(responses[j].resp);
        free(responses);
        return PAM_CONV_ERR;
    }
    *result = responses;
    return PAM_SUCCESS;
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    char *password = NULL;
    size_t capacity = 0;
    ssize_t length = getline(&password, &capacity, stdin);
    if (length < 2 || length > 1024 || password[length - 1] != '\n' ||
        memchr(password, '\0', (size_t)length - 1) != NULL) {
        if (password) {
            explicit_bzero(password, capacity);
            free(password);
        }
        return 1;
    }
    password[length - 1] = '\0';
    struct pam_conv conversation = {password_conversation, password};
    pam_handle_t *handle = NULL;
    int status = pam_start("face-unlock-password", argv[1], &conversation, &handle);
    if (status == PAM_SUCCESS) status = pam_authenticate(handle, 0);
    if (status == PAM_SUCCESS) status = pam_acct_mgmt(handle, 0);
    if (handle) pam_end(handle, status);
    explicit_bzero(password, capacity);
    free(password);
    return status == PAM_SUCCESS ? 0 : 1;
}
