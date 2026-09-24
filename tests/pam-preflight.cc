// Run only in a disposable root container: fixtures use the package model path.
#include <INIReader.h>
#include <security/pam_appl.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <unistd.h>
int check_enabled(const INIReader &, const char *, const char *);
int main() {
  if (geteuid() != 0) return 77;
  std::filesystem::create_directories("/var/lib/face-unlock/models");
  const char *user = "face-unlock-preflight-test";
  const char *model = "/var/lib/face-unlock/models/face-unlock-preflight-test.dat";
  std::ofstream(model) << "[]";
  for (const auto *device : {"none", "/missing-camera", "/tmp", "/dev/null"}) {
    std::ofstream config("/tmp/face-unlock-preflight.ini");
    config << "[core]\nabort_if_ssh=false\nabort_if_lid_closed=false\n"
              "[video]\ndevice_path=" << device << "\n";
    config.close();
    INIReader reader("/tmp/face-unlock-preflight.ini");
    int expected = std::string(device) == "/dev/null" ? PAM_SUCCESS : PAM_AUTHINFO_UNAVAIL;
    int actual = check_enabled(reader, user, "login");
    if (actual != expected) {
      std::cerr << device << ": expected " << expected << ", got " << actual << "\n";
      return 1;
    }
  }
  std::ofstream remote_config("/tmp/face-unlock-preflight.ini");
  remote_config << "[core]\nabort_if_ssh=true\nabort_if_lid_closed=false\n"
                   "[video]\ndevice_path=/dev/null\n";
  remote_config.close();
  INIReader reader("/tmp/face-unlock-preflight.ini");
  if (check_enabled(reader, user, "sshd") != PAM_AUTHINFO_UNAVAIL) return 1;
  if (check_enabled(reader, user, "face-unlock-password") != PAM_AUTHINFO_UNAVAIL) return 1;
  std::filesystem::remove(model);
  if (check_enabled(reader, user, "login") != PAM_AUTHINFO_UNAVAIL) return 1;
  std::cout << "Camera and model preflight checks passed\n";
}
